"""
Unified Knowledge Ingestion System - All Knowledge Pathways into Grace

This system unifies all ways Grace acquires knowledge:
1. Sandbox Practice - Self-generated learning
2. Oracle/LLM - External LLM knowledge on request
3. Federated Learning - Cross-domain pattern transfer
4. File Ingestion - Documents and code
5. GitHub Extractor - Real-world patterns
6. Self-Healing Cycles - Fix patterns
7. User Feedback - Corrections and ratings
8. Simulation Engine - Synthetic scenarios (NEW)
9. Replay Learning - Learn from past failures (NEW)
10. Self-Distillation - Compress and refine knowledge (NEW)
11. Multi-Agent Debate - Consensus through debate (NEW)
12. Benchmark Mining - Extract from benchmarks (NEW)

ALL operations tracked with Genesis Keys for full provenance.
"""

import logging
import json
import uuid
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import time
import random
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class IngestionSource(str, Enum):
    """All sources of knowledge ingestion."""
    # Current sources
    SANDBOX_PRACTICE = "sandbox_practice"
    ORACLE_LLM = "oracle_llm"
    FEDERATED_LEARNING = "federated_learning"
    FILE_INGESTION = "file_ingestion"
    GITHUB_EXTRACTOR = "github_extractor"
    SELF_HEALING = "self_healing"
    USER_FEEDBACK = "user_feedback"
    EXTERNAL_KNOWLEDGE = "external_knowledge"
    
    # New sources
    SIMULATION_ENGINE = "simulation_engine"
    REPLAY_LEARNING = "replay_learning"
    SELF_DISTILLATION = "self_distillation"
    MULTI_AGENT_DEBATE = "multi_agent_debate"
    BENCHMARK_MINING = "benchmark_mining"
    STREAM_PROCESSING = "stream_processing"
    GENETIC_EVOLUTION = "genetic_evolution"
    CURRICULUM_RL = "curriculum_rl"
    
    # On-demand
    LLM_ON_REQUEST = "llm_on_request"


class KnowledgeType(str, Enum):
    """Types of knowledge that can be ingested."""
    PATTERN = "pattern"
    PROCEDURE = "procedure"
    TEMPLATE = "template"
    FACT = "fact"
    CONCEPT = "concept"
    FIX = "fix"
    EXAMPLE = "example"
    REASONING = "reasoning"
    CODE = "code"
    DOCUMENTATION = "documentation"


@dataclass
class KnowledgeItem:
    """
    A single item of knowledge to be ingested.
    This is the normalized format for all ingestion sources.
    """
    item_id: str
    source: IngestionSource
    knowledge_type: KnowledgeType
    content: str
    context: Dict[str, Any]
    
    # Provenance
    genesis_key_id: Optional[str] = None
    source_url: Optional[str] = None
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Quality
    confidence: float = 0.5
    trust_score: float = 0.5
    quality_score: float = 0.5
    
    # Evidence
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tags and categorization
    domain: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    ingested_at: Optional[datetime] = None
    
    @staticmethod
    def create(
        source: IngestionSource,
        knowledge_type: KnowledgeType,
        content: str,
        **kwargs
    ) -> "KnowledgeItem":
        """Factory method to create a knowledge item."""
        return KnowledgeItem(
            item_id=f"KI-{uuid.uuid4().hex[:12]}",
            source=source,
            knowledge_type=knowledge_type,
            content=content,
            context=kwargs.get("context", {}),
            confidence=kwargs.get("confidence", 0.5),
            domain=kwargs.get("domain"),
            tags=kwargs.get("tags", []),
            evidence=kwargs.get("evidence", []),
            source_metadata=kwargs.get("source_metadata", {})
        )


@dataclass
class IngestionResult:
    """Result of ingesting a knowledge item."""
    success: bool
    item_id: str
    genesis_key_id: Optional[str] = None
    stored_as: Optional[str] = None  # pattern, procedure, etc.
    trust_score: float = 0.0
    deduplicated: bool = False
    merged_with: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# GENESIS KEY INTEGRATION
# =============================================================================

class GenesisKeyTracker:
    """Track all ingestion with Genesis Keys."""
    
    def __init__(self, session=None):
        self.session = session
        self._genesis_service = None
    
    @property
    def genesis_service(self):
        """Lazy load genesis service."""
        if self._genesis_service is None:
            try:
                from genesis.genesis_key_service import get_genesis_service
                self._genesis_service = get_genesis_service()
            except Exception as e:
                logger.warning(f"Genesis service not available: {e}")
        return self._genesis_service
    
    def create_ingestion_key(
        self,
        source: IngestionSource,
        what: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        tags: List[str] = None
    ) -> Optional[str]:
        """Create a Genesis Key for an ingestion operation."""
        if not self.genesis_service:
            return None
        
        try:
            from models.genesis_key_models import GenesisKeyType
            
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.LEARNING,
                what_description=f"Knowledge ingestion: {what}",
                who_actor=f"unified_ingestion/{source.value}",
                where_location="cognitive/unified_knowledge_ingestion",
                why_reason=f"Ingesting knowledge from {source.value}",
                how_method="unified_knowledge_ingestion",
                input_data=input_data,
                output_data=output_data,
                tags=tags or [source.value, "ingestion", "learning"],
                session=self.session
            )
            return key.key_id if key else None
        except Exception as e:
            logger.warning(f"Failed to create Genesis Key: {e}")
            return None


# =============================================================================
# LLM ON-REQUEST KNOWLEDGE
# =============================================================================

class LLMKnowledgeRequester:
    """
    Request knowledge from LLM on demand.
    Grace can ask the LLM for specific knowledge when needed.
    """
    
    def __init__(self, llm_orchestrator=None, session=None):
        self.llm_orchestrator = llm_orchestrator
        self.session = session
        self.genesis_tracker = GenesisKeyTracker(session)
        
        # Request templates
        self.request_templates = {
            "explain_concept": "Explain the concept of {topic} in the context of {domain}. Provide examples and best practices.",
            "code_pattern": "What is the best pattern for {task} in {language}? Provide code examples.",
            "fix_strategy": "What is the best strategy to fix {issue_type} errors? Provide step-by-step approach.",
            "best_practices": "What are the best practices for {topic}? List the top 5 with explanations.",
            "compare": "Compare {option_a} vs {option_b} for {use_case}. Which is better and why?",
            "debug_help": "How do I debug {error_type} in {context}? Provide diagnostic steps.",
            "architecture": "What is the best architecture for {system_type}? Provide design patterns.",
            "security": "What are the security considerations for {topic}? List vulnerabilities and mitigations."
        }
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "knowledge_items_created": 0,
            "by_template": {}
        }
    
    async def request_knowledge(
        self,
        topic: str,
        template: str = "explain_concept",
        context: Dict[str, Any] = None,
        domain: str = None,
        **kwargs
    ) -> List[KnowledgeItem]:
        """
        Request knowledge from LLM on a specific topic.
        
        Args:
            topic: What to learn about
            template: Request template to use
            context: Additional context
            domain: Knowledge domain
            **kwargs: Template parameters
            
        Returns:
            List of knowledge items extracted from LLM response
        """
        context = context or {}
        items = []
        
        # Build prompt from template
        if template in self.request_templates:
            prompt_template = self.request_templates[template]
            prompt = prompt_template.format(topic=topic, **kwargs)
        else:
            prompt = f"Explain {topic}"
        
        # Add context
        if domain:
            prompt += f"\n\nContext: This is for {domain} domain."
        
        self.stats["total_requests"] += 1
        self.stats["by_template"][template] = self.stats["by_template"].get(template, 0) + 1
        
        try:
            # Call LLM
            if self.llm_orchestrator:
                response = await self.llm_orchestrator.generate(
                    prompt=prompt,
                    system_prompt="You are a knowledge expert. Provide clear, structured, actionable knowledge.",
                    max_tokens=2000
                )
                content = response.get("content", "")
            else:
                # Fallback for testing
                content = f"Knowledge about {topic}: [Placeholder - LLM not available]"
            
            if content:
                # Create knowledge item
                item = KnowledgeItem.create(
                    source=IngestionSource.LLM_ON_REQUEST,
                    knowledge_type=self._determine_knowledge_type(template),
                    content=content,
                    context={"topic": topic, "template": template, "prompt": prompt},
                    domain=domain,
                    tags=[topic, template, domain] if domain else [topic, template],
                    confidence=0.8,
                    source_metadata={"template": template, "llm_response": True}
                )
                
                # Track with Genesis Key
                genesis_key = self.genesis_tracker.create_ingestion_key(
                    source=IngestionSource.LLM_ON_REQUEST,
                    what=f"Requested knowledge: {topic}",
                    input_data={"topic": topic, "template": template, "prompt": prompt},
                    output_data={"item_id": item.item_id, "content_length": len(content)},
                    tags=["llm_request", topic]
                )
                item.genesis_key_id = genesis_key
                
                items.append(item)
                self.stats["successful_requests"] += 1
                self.stats["knowledge_items_created"] += 1
                
                logger.info(f"LLM knowledge request: {topic} -> {len(content)} chars")
        
        except Exception as e:
            logger.error(f"LLM knowledge request failed: {e}")
        
        return items
    
    def _determine_knowledge_type(self, template: str) -> KnowledgeType:
        """Determine knowledge type from template."""
        type_map = {
            "explain_concept": KnowledgeType.CONCEPT,
            "code_pattern": KnowledgeType.PATTERN,
            "fix_strategy": KnowledgeType.PROCEDURE,
            "best_practices": KnowledgeType.FACT,
            "compare": KnowledgeType.REASONING,
            "debug_help": KnowledgeType.PROCEDURE,
            "architecture": KnowledgeType.PATTERN,
            "security": KnowledgeType.FACT
        }
        return type_map.get(template, KnowledgeType.CONCEPT)


# =============================================================================
# SIMULATION ENGINE (NEW)
# =============================================================================

class SimulationEngine:
    """
    Generate synthetic scenarios for training.
    Creates edge cases, failure scenarios, and novel problems.
    """
    
    def __init__(self, session=None):
        self.session = session
        self.genesis_tracker = GenesisKeyTracker(session)
        
        # Scenario generators
        self.scenario_types = {
            "edge_case": self._generate_edge_case,
            "failure_scenario": self._generate_failure_scenario,
            "performance_stress": self._generate_performance_stress,
            "security_attack": self._generate_security_attack,
            "concurrency_issue": self._generate_concurrency_issue,
            "data_corruption": self._generate_data_corruption,
            "integration_failure": self._generate_integration_failure,
            "resource_exhaustion": self._generate_resource_exhaustion
        }
        
        self.stats = {
            "scenarios_generated": 0,
            "by_type": {}
        }
    
    def generate_scenario(
        self,
        scenario_type: str,
        domain: str = "general",
        difficulty: str = "medium",
        count: int = 1
    ) -> List[KnowledgeItem]:
        """
        Generate synthetic training scenarios.
        
        Args:
            scenario_type: Type of scenario to generate
            domain: Domain context
            difficulty: easy, medium, hard, extreme
            count: Number of scenarios to generate
            
        Returns:
            List of knowledge items representing scenarios
        """
        items = []
        
        generator = self.scenario_types.get(scenario_type, self._generate_generic)
        
        for i in range(count):
            try:
                scenario = generator(domain, difficulty)
                
                item = KnowledgeItem.create(
                    source=IngestionSource.SIMULATION_ENGINE,
                    knowledge_type=KnowledgeType.EXAMPLE,
                    content=json.dumps(scenario),
                    context={"scenario_type": scenario_type, "difficulty": difficulty},
                    domain=domain,
                    tags=["simulation", scenario_type, difficulty],
                    confidence=0.9,  # Synthetic data is controlled
                    source_metadata={"generated": True, "iteration": i}
                )
                
                # Track with Genesis Key
                genesis_key = self.genesis_tracker.create_ingestion_key(
                    source=IngestionSource.SIMULATION_ENGINE,
                    what=f"Generated scenario: {scenario_type}",
                    input_data={"type": scenario_type, "domain": domain, "difficulty": difficulty},
                    output_data={"item_id": item.item_id, "scenario": scenario},
                    tags=["simulation", scenario_type]
                )
                item.genesis_key_id = genesis_key
                
                items.append(item)
                self.stats["scenarios_generated"] += 1
                self.stats["by_type"][scenario_type] = self.stats["by_type"].get(scenario_type, 0) + 1
                
            except Exception as e:
                logger.error(f"Scenario generation failed: {e}")
        
        return items
    
    def _generate_edge_case(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate edge case scenario."""
        edge_cases = {
            "coding": [
                {"case": "empty_input", "input": "", "expected": "handle gracefully"},
                {"case": "null_value", "input": None, "expected": "check for null"},
                {"case": "max_int", "input": 2**31-1, "expected": "handle overflow"},
                {"case": "unicode", "input": "🎉émoji", "expected": "handle unicode"},
                {"case": "very_long", "input": "a" * 10000, "expected": "handle length"}
            ],
            "general": [
                {"case": "boundary", "description": "Test at boundaries"},
                {"case": "empty", "description": "Empty/null inputs"},
                {"case": "overflow", "description": "Numeric overflow"}
            ]
        }
        cases = edge_cases.get(domain, edge_cases["general"])
        return random.choice(cases)
    
    def _generate_failure_scenario(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate failure scenario."""
        return {
            "failure_type": random.choice(["timeout", "exception", "assertion", "crash"]),
            "trigger": f"Condition that causes failure in {domain}",
            "expected_recovery": "How to recover",
            "difficulty": difficulty
        }
    
    def _generate_performance_stress(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate performance stress scenario."""
        multipliers = {"easy": 10, "medium": 100, "hard": 1000, "extreme": 10000}
        return {
            "load_multiplier": multipliers.get(difficulty, 100),
            "concurrent_users": random.randint(10, 1000),
            "data_size_mb": random.randint(1, 1000),
            "expected_latency_ms": random.randint(10, 5000)
        }
    
    def _generate_security_attack(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate security attack scenario."""
        attacks = ["sql_injection", "xss", "csrf", "path_traversal", "buffer_overflow"]
        return {
            "attack_type": random.choice(attacks),
            "payload": f"Example {random.choice(attacks)} payload",
            "vulnerability": "Description of vulnerability",
            "mitigation": "How to prevent"
        }
    
    def _generate_concurrency_issue(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate concurrency issue scenario."""
        return {
            "issue_type": random.choice(["race_condition", "deadlock", "livelock", "starvation"]),
            "threads": random.randint(2, 100),
            "shared_resource": "Description of shared resource",
            "expected_solution": "Synchronization approach"
        }
    
    def _generate_data_corruption(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate data corruption scenario."""
        return {
            "corruption_type": random.choice(["partial_write", "encoding_error", "truncation"]),
            "data_type": random.choice(["json", "binary", "text", "database"]),
            "detection_method": "How to detect",
            "recovery_method": "How to recover"
        }
    
    def _generate_integration_failure(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate integration failure scenario."""
        return {
            "failure_point": random.choice(["api", "database", "cache", "queue", "external_service"]),
            "error_code": random.randint(400, 599),
            "retry_strategy": "Exponential backoff",
            "fallback": "Graceful degradation approach"
        }
    
    def _generate_resource_exhaustion(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate resource exhaustion scenario."""
        return {
            "resource": random.choice(["memory", "cpu", "disk", "network", "file_handles"]),
            "threshold": random.randint(80, 100),
            "symptoms": "How it manifests",
            "prevention": "How to prevent"
        }
    
    def _generate_generic(self, domain: str, difficulty: str) -> Dict[str, Any]:
        """Generate generic scenario."""
        return {
            "type": "generic",
            "domain": domain,
            "difficulty": difficulty,
            "description": f"Generic scenario for {domain}"
        }


# =============================================================================
# REPLAY LEARNING (NEW)
# =============================================================================

class ReplayLearner:
    """
    Learn from past failures by replaying them with new knowledge.
    Implements experience replay for continuous improvement.
    """
    
    def __init__(self, session=None, learning_memory=None):
        self.session = session
        self.learning_memory = learning_memory
        self.genesis_tracker = GenesisKeyTracker(session)
        
        # Failure buffer (circular buffer)
        self.failure_buffer: List[Dict[str, Any]] = []
        self.buffer_max_size = 10000
        
        # Replay statistics
        self.stats = {
            "failures_recorded": 0,
            "replays_attempted": 0,
            "successful_replays": 0,
            "knowledge_extracted": 0
        }
    
    def record_failure(
        self,
        task: Dict[str, Any],
        attempt: Dict[str, Any],
        error: str,
        context: Dict[str, Any] = None
    ):
        """Record a failure for later replay."""
        failure = {
            "failure_id": f"FAIL-{uuid.uuid4().hex[:8]}",
            "task": task,
            "attempt": attempt,
            "error": error,
            "context": context or {},
            "recorded_at": datetime.utcnow().isoformat(),
            "replay_count": 0,
            "last_replayed": None
        }
        
        self.failure_buffer.append(failure)
        if len(self.failure_buffer) > self.buffer_max_size:
            self.failure_buffer.pop(0)
        
        self.stats["failures_recorded"] += 1
        logger.info(f"Recorded failure: {failure['failure_id']}")
    
    def replay_failures(
        self,
        count: int = 10,
        strategy: str = "random",
        executor: Callable = None
    ) -> List[KnowledgeItem]:
        """
        Replay past failures with current knowledge.
        
        Args:
            count: Number of failures to replay
            strategy: Selection strategy (random, oldest, most_recent, least_replayed)
            executor: Function to re-attempt the task
            
        Returns:
            Knowledge items from successful replays
        """
        items = []
        
        if not self.failure_buffer:
            return items
        
        # Select failures to replay
        selected = self._select_failures(count, strategy)
        
        for failure in selected:
            self.stats["replays_attempted"] += 1
            failure["replay_count"] += 1
            failure["last_replayed"] = datetime.utcnow().isoformat()
            
            try:
                # Re-attempt with current knowledge
                if executor:
                    result = executor(failure["task"], failure["context"])
                    success = result.get("success", False)
                else:
                    # Analyze the failure without executor
                    analysis = self._analyze_failure_error(failure)
                    success = analysis.get("auto_fixable", False)
                    result = analysis
                
                if success:
                    self.stats["successful_replays"] += 1
                    
                    # Extract knowledge from successful replay
                    item = KnowledgeItem.create(
                        source=IngestionSource.REPLAY_LEARNING,
                        knowledge_type=KnowledgeType.FIX,
                        content=json.dumps({
                            "original_error": failure["error"],
                            "solution": result,
                            "learning": f"Fixed after {failure['replay_count']} replays"
                        }),
                        context=failure["context"],
                        tags=["replay", "counterfactual", "recovery"],
                        confidence=0.85,
                        source_metadata={"failure_id": failure["failure_id"]}
                    )
                    
                    # Track with Genesis Key
                    genesis_key = self.genesis_tracker.create_ingestion_key(
                        source=IngestionSource.REPLAY_LEARNING,
                        what=f"Replay success: {failure['failure_id']}",
                        input_data={"failure_id": failure["failure_id"], "error": failure["error"]},
                        output_data={"item_id": item.item_id, "solution": str(result)[:500]},
                        tags=["replay", "learning"]
                    )
                    item.genesis_key_id = genesis_key
                    
                    items.append(item)
                    self.stats["knowledge_extracted"] += 1
                    
                    # Remove from buffer - we've learned from it
                    self.failure_buffer.remove(failure)
                    
            except Exception as e:
                logger.error(f"Replay failed: {e}")
        
        return items
    
    def _select_failures(self, count: int, strategy: str) -> List[Dict]:
        """Select failures based on strategy."""
        if not self.failure_buffer:
            return []
        
        if strategy == "random":
            return random.sample(self.failure_buffer, min(count, len(self.failure_buffer)))
        elif strategy == "oldest":
            return sorted(self.failure_buffer, key=lambda x: x["recorded_at"])[:count]
        elif strategy == "most_recent":
            return sorted(self.failure_buffer, key=lambda x: x["recorded_at"], reverse=True)[:count]
        elif strategy == "least_replayed":
            return sorted(self.failure_buffer, key=lambda x: x["replay_count"])[:count]
        else:
            return self.failure_buffer[:count]
    
    def _analyze_failure_error(self, failure: Dict) -> Dict[str, Any]:
        """
        Analyze a failure to understand what went wrong and suggest fixes.
        
        Parses error messages, identifies patterns, and suggests remediation.
        """
        error_message = failure.get("error", "")
        task = failure.get("task", {})
        context = failure.get("context", {})
        
        analysis = {
            "error_type": None,
            "error_category": None,
            "line_number": None,
            "variable_name": None,
            "suggested_fixes": [],
            "auto_fixable": False,
            "confidence": 0.0,
            "analysis": ""
        }
        
        error_lower = error_message.lower()
        
        # Common error pattern detection
        error_patterns = [
            (r"syntaxerror|invalid syntax", "syntax", "SyntaxError"),
            (r"nameerror|name\s+'(\w+)'\s+is not defined", "name", "NameError"),
            (r"typeerror", "type", "TypeError"),
            (r"valueerror", "value", "ValueError"),
            (r"keyerror", "key", "KeyError"),
            (r"indexerror|list index out of range", "index", "IndexError"),
            (r"attributeerror|has no attribute", "attribute", "AttributeError"),
            (r"importerror|no module named", "import", "ImportError"),
            (r"indentationerror|unexpected indent", "indentation", "IndentationError"),
            (r"zerodivisionerror|division by zero", "division", "ZeroDivisionError"),
            (r"assertionerror", "assertion", "AssertionError"),
            (r"timeout|timed out", "timeout", "TimeoutError"),
            (r"connection.*refused|connection.*error", "connection", "ConnectionError"),
        ]
        
        for pattern, category, error_type in error_patterns:
            if re.search(pattern, error_lower):
                analysis["error_category"] = category
                analysis["error_type"] = error_type
                break
        
        # Extract line number
        line_match = re.search(r'line\s+(\d+)', error_message, re.IGNORECASE)
        if line_match:
            analysis["line_number"] = int(line_match.group(1))
        
        # Extract variable/function name
        name_match = re.search(r"name\s+'(\w+)'\s+is not defined", error_message, re.IGNORECASE)
        if name_match:
            analysis["variable_name"] = name_match.group(1)
        
        # Generate suggested fixes based on error type
        fixes = self._get_suggested_fixes(analysis, error_message, task)
        analysis["suggested_fixes"] = fixes
        analysis["auto_fixable"] = len(fixes) > 0 and analysis["error_category"] in ["syntax", "indentation", "import"]
        analysis["confidence"] = 0.8 if analysis["error_type"] else 0.3
        
        # Build analysis summary
        analysis["analysis"] = self._build_analysis_summary(analysis, failure)
        
        return analysis
    
    def _get_suggested_fixes(self, analysis: Dict, error_message: str, task: Dict) -> List[Dict]:
        """Generate suggested fixes based on error analysis."""
        fixes = []
        category = analysis.get("error_category")
        
        fix_suggestions = {
            "syntax": [
                {"fix": "Check for missing colons, parentheses, or brackets", "confidence": 0.7},
                {"fix": "Verify string quotes are properly closed", "confidence": 0.6},
                {"fix": "Check for invalid characters in identifiers", "confidence": 0.5},
            ],
            "name": [
                {"fix": f"Define '{analysis.get('variable_name', 'variable')}' before use", "confidence": 0.8},
                {"fix": "Check for typos in variable/function names", "confidence": 0.7},
                {"fix": "Import the required module", "confidence": 0.6},
            ],
            "type": [
                {"fix": "Check argument types match expected types", "confidence": 0.7},
                {"fix": "Add type conversion (int, str, float)", "confidence": 0.6},
                {"fix": "Verify None checks before operations", "confidence": 0.6},
            ],
            "import": [
                {"fix": "Install missing package with pip", "confidence": 0.9},
                {"fix": "Check module name spelling", "confidence": 0.7},
                {"fix": "Verify PYTHONPATH includes module location", "confidence": 0.5},
            ],
            "indentation": [
                {"fix": "Use consistent spaces (4 spaces recommended)", "confidence": 0.9},
                {"fix": "Check for mixed tabs and spaces", "confidence": 0.8},
                {"fix": "Align code blocks properly", "confidence": 0.7},
            ],
            "key": [
                {"fix": "Check if key exists before access with .get() or 'in'", "confidence": 0.9},
                {"fix": "Verify dictionary keys match expected values", "confidence": 0.7},
            ],
            "index": [
                {"fix": "Check list length before indexing", "confidence": 0.9},
                {"fix": "Use negative indexing carefully", "confidence": 0.6},
            ],
            "attribute": [
                {"fix": "Verify object type has expected attribute", "confidence": 0.7},
                {"fix": "Check for None before accessing attributes", "confidence": 0.8},
            ],
        }
        
        if category in fix_suggestions:
            fixes = fix_suggestions[category]
        else:
            fixes = [
                {"fix": "Review error message and stack trace", "confidence": 0.5},
                {"fix": "Check recent code changes", "confidence": 0.4},
            ]
        
        return fixes
    
    def _build_analysis_summary(self, analysis: Dict, failure: Dict) -> str:
        """Build a human-readable analysis summary."""
        parts = []
        
        if analysis["error_type"]:
            parts.append(f"Error Type: {analysis['error_type']}")
        
        if analysis["line_number"]:
            parts.append(f"Location: Line {analysis['line_number']}")
        
        if analysis["variable_name"]:
            parts.append(f"Undefined: '{analysis['variable_name']}'")
        
        if analysis["suggested_fixes"]:
            top_fix = analysis["suggested_fixes"][0]
            parts.append(f"Suggested Fix: {top_fix['fix']}")
        
        parts.append(f"Auto-fixable: {'Yes' if analysis['auto_fixable'] else 'No'}")
        parts.append(f"Replay Count: {failure.get('replay_count', 0)}")
        
        return " | ".join(parts)


# =============================================================================
# SELF-DISTILLATION (NEW)
# =============================================================================

class SelfDistiller:
    """
    Grace distills her own knowledge - compresses and refines patterns.
    Similar to knowledge distillation in neural networks.
    """
    
    def __init__(self, session=None, learning_memory=None):
        self.session = session
        self.learning_memory = learning_memory
        self.genesis_tracker = GenesisKeyTracker(session)
        
        self.stats = {
            "patterns_distilled": 0,
            "compression_ratio": 0.0,
            "quality_improvement": 0.0
        }
    
    def distill_patterns(
        self,
        domain: str = None,
        min_sample_size: int = 5,
        similarity_threshold: float = 0.8
    ) -> List[KnowledgeItem]:
        """
        Distill similar patterns into refined, compressed versions.
        
        Args:
            domain: Domain to distill (None for all)
            min_sample_size: Minimum patterns to merge
            similarity_threshold: How similar patterns must be
            
        Returns:
            Distilled knowledge items
        """
        items = []
        
        # Get existing patterns
        patterns = self._get_patterns(domain)
        
        if len(patterns) < min_sample_size:
            return items
        
        # Group similar patterns
        groups = self._group_similar_patterns(patterns, similarity_threshold)
        
        for group in groups:
            if len(group) >= min_sample_size:
                # Distill group into single refined pattern
                distilled = self._distill_group(group)
                
                if distilled:
                    item = KnowledgeItem.create(
                        source=IngestionSource.SELF_DISTILLATION,
                        knowledge_type=KnowledgeType.PATTERN,
                        content=distilled["content"],
                        context={"source_patterns": len(group), "confidence_boost": distilled["confidence_boost"]},
                        domain=domain,
                        tags=["distilled", "refined", "compressed"],
                        confidence=distilled["confidence"],
                        source_metadata={"source_pattern_ids": [p.get("id") for p in group]}
                    )
                    
                    # Track with Genesis Key
                    genesis_key = self.genesis_tracker.create_ingestion_key(
                        source=IngestionSource.SELF_DISTILLATION,
                        what=f"Distilled {len(group)} patterns",
                        input_data={"pattern_count": len(group), "domain": domain},
                        output_data={"item_id": item.item_id, "compression": len(group)},
                        tags=["distillation", "compression"]
                    )
                    item.genesis_key_id = genesis_key
                    
                    items.append(item)
                    self.stats["patterns_distilled"] += len(group)
        
        return items
    
    def _get_patterns(self, domain: str = None) -> List[Dict]:
        """Get existing patterns from learning memory."""
        if self.learning_memory:
            try:
                return self.learning_memory.get_patterns(domain=domain)
            except:
                pass
        return []
    
    def _group_similar_patterns(self, patterns: List[Dict], threshold: float) -> List[List[Dict]]:
        """Group similar patterns together using text similarity or embeddings."""
        groups = []
        used = set()
        
        # Pre-compute embeddings if available for better similarity matching
        embeddings = self._get_pattern_embeddings(patterns)
        
        for i, p1 in enumerate(patterns):
            if i in used:
                continue
            group = [p1]
            used.add(i)
            
            for j, p2 in enumerate(patterns[i+1:], i+1):
                if j not in used:
                    # Use embeddings if available, otherwise text similarity
                    if embeddings and i in embeddings and j in embeddings:
                        similarity = self._cosine_similarity(embeddings[i], embeddings[j])
                    else:
                        similarity = self._calculate_similarity(p1, p2)
                    
                    if similarity >= threshold:
                        group.append(p2)
                        used.add(j)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _calculate_similarity(self, p1: Dict, p2: Dict) -> float:
        """Calculate similarity between two patterns using multiple methods."""
        content1 = str(p1.get("content", ""))
        content2 = str(p2.get("content", ""))
        
        if not content1 or not content2:
            return 0.0
        
        # Method 1: SequenceMatcher for text similarity (best for code/structured text)
        sequence_ratio = SequenceMatcher(None, content1.lower(), content2.lower()).ratio()
        
        # Method 2: Jaccard similarity (word overlap)
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        if words1 and words2:
            jaccard = len(words1 & words2) / len(words1 | words2)
        else:
            jaccard = 0.0
        
        # Method 3: Tag similarity if available
        tags1 = set(p1.get("tags", []))
        tags2 = set(p2.get("tags", []))
        if tags1 and tags2:
            tag_similarity = len(tags1 & tags2) / len(tags1 | tags2)
        else:
            tag_similarity = 0.0
        
        # Weighted combination (sequence match is most reliable for code patterns)
        combined = (sequence_ratio * 0.5) + (jaccard * 0.3) + (tag_similarity * 0.2)
        
        return combined
    
    def _get_pattern_embeddings(self, patterns: List[Dict]) -> Optional[Dict[int, List[float]]]:
        """Get embeddings for patterns if embedding model is available."""
        try:
            from embedding import get_embedding_model
            embedder = get_embedding_model()
            if embedder is None:
                return None
            
            embeddings = {}
            for i, p in enumerate(patterns):
                content = str(p.get("content", ""))
                if content:
                    try:
                        embedding = embedder.embed(content)
                        if embedding is not None:
                            embeddings[i] = embedding
                    except Exception:
                        continue
            
            return embeddings if embeddings else None
        except ImportError:
            return None
        except Exception as e:
            logger.debug(f"Failed to get embeddings: {e}")
            return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _distill_group(self, group: List[Dict]) -> Optional[Dict]:
        """Distill a group of patterns into one refined pattern."""
        if not group:
            return None
        
        # Combine content (would use LLM for better distillation)
        contents = [str(p.get("content", "")) for p in group]
        
        # Find common elements
        all_words = []
        for c in contents:
            all_words.extend(c.split())
        
        # Count word frequency
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Keep most common words
        common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        distilled_content = " ".join([w[0] for w in common_words])
        
        # Calculate confidence (average + bonus for consensus)
        confidences = [p.get("trust_score", 0.5) for p in group]
        avg_confidence = sum(confidences) / len(confidences)
        consensus_bonus = min(0.2, len(group) * 0.02)
        
        return {
            "content": f"Distilled pattern from {len(group)} sources: {distilled_content}",
            "confidence": min(0.95, avg_confidence + consensus_bonus),
            "confidence_boost": consensus_bonus
        }


# =============================================================================
# MULTI-AGENT DEBATE (NEW)
# =============================================================================

class MultiAgentDebater:
    """
    Multiple Grace instances debate to reach better conclusions.
    Improves reasoning through adversarial questioning.
    """
    
    def __init__(self, session=None, llm_orchestrator=None):
        self.session = session
        self.llm_orchestrator = llm_orchestrator
        self.genesis_tracker = GenesisKeyTracker(session)
        
        # Debate configuration
        self.num_agents = 3
        self.max_rounds = 5
        
        self.stats = {
            "debates_held": 0,
            "consensus_reached": 0,
            "knowledge_refined": 0
        }
    
    async def debate_topic(
        self,
        topic: str,
        initial_positions: List[str] = None,
        domain: str = None
    ) -> List[KnowledgeItem]:
        """
        Hold a debate on a topic to reach refined understanding.
        
        Args:
            topic: Topic to debate
            initial_positions: Starting positions for each agent
            domain: Knowledge domain
            
        Returns:
            Knowledge items from debate conclusions
        """
        items = []
        
        # Initialize debate
        debate_id = f"DEBATE-{uuid.uuid4().hex[:8]}"
        self.stats["debates_held"] += 1
        
        # Create initial positions if not provided
        if not initial_positions:
            initial_positions = [
                f"Position A: {topic} - conservative approach",
                f"Position B: {topic} - aggressive approach",
                f"Position C: {topic} - balanced approach"
            ]
        
        # Run debate rounds
        positions = initial_positions[:self.num_agents]
        debate_history = []
        
        for round_num in range(self.max_rounds):
            round_arguments = []
            
            for i, position in enumerate(positions):
                # Generate argument (would use LLM)
                argument = await self._generate_argument(
                    agent_id=i,
                    position=position,
                    topic=topic,
                    history=debate_history
                )
                round_arguments.append(argument)
            
            debate_history.append({
                "round": round_num + 1,
                "arguments": round_arguments
            })
            
            # Check for consensus
            if self._check_consensus(round_arguments):
                self.stats["consensus_reached"] += 1
                break
        
        # Extract conclusion
        conclusion = self._extract_conclusion(debate_history)
        
        if conclusion:
            item = KnowledgeItem.create(
                source=IngestionSource.MULTI_AGENT_DEBATE,
                knowledge_type=KnowledgeType.REASONING,
                content=conclusion["content"],
                context={
                    "debate_id": debate_id,
                    "rounds": len(debate_history),
                    "consensus": conclusion.get("consensus", False)
                },
                domain=domain,
                tags=["debate", "reasoning", "consensus"],
                confidence=conclusion.get("confidence", 0.7),
                evidence=[{"debate_history": debate_history}]
            )
            
            # Track with Genesis Key
            genesis_key = self.genesis_tracker.create_ingestion_key(
                source=IngestionSource.MULTI_AGENT_DEBATE,
                what=f"Debate conclusion: {topic[:50]}",
                input_data={"topic": topic, "rounds": len(debate_history)},
                output_data={"item_id": item.item_id, "consensus": conclusion.get("consensus")},
                tags=["debate", "reasoning"]
            )
            item.genesis_key_id = genesis_key
            
            items.append(item)
            self.stats["knowledge_refined"] += 1
        
        return items
    
    async def _generate_argument(
        self,
        agent_id: int,
        position: str,
        topic: str,
        history: List[Dict]
    ) -> Dict[str, Any]:
        """Generate an argument for a debate round."""
        # Would use LLM in production
        return {
            "agent_id": agent_id,
            "position": position,
            "argument": f"Agent {agent_id} argues: {position}",
            "counterpoints": [],
            "confidence": random.uniform(0.6, 0.9)
        }
    
    def _check_consensus(self, arguments: List[Dict]) -> bool:
        """Check if agents have reached consensus."""
        if len(arguments) < 2:
            return True
        
        # Simple check - all confidences above threshold
        confidences = [a.get("confidence", 0) for a in arguments]
        return min(confidences) > 0.8 and max(confidences) - min(confidences) < 0.1
    
    def _extract_conclusion(self, history: List[Dict]) -> Optional[Dict]:
        """Extract conclusion from debate history."""
        if not history:
            return None
        
        last_round = history[-1]
        arguments = last_round.get("arguments", [])
        
        if not arguments:
            return None
        
        # Find highest confidence argument
        best = max(arguments, key=lambda x: x.get("confidence", 0))
        
        return {
            "content": f"Debate conclusion: {best.get('argument', '')}",
            "consensus": len(history) < self.max_rounds,
            "confidence": best.get("confidence", 0.7)
        }


# =============================================================================
# BENCHMARK MINING (NEW)
# =============================================================================

class BenchmarkMiner:
    """
    Extract patterns from coding benchmarks (HumanEval, MBPP, etc.).
    Learn from solved problems.
    """
    
    def __init__(self, session=None):
        self.session = session
        self.genesis_tracker = GenesisKeyTracker(session)
        
        self.stats = {
            "benchmarks_processed": 0,
            "patterns_extracted": 0,
            "templates_created": 0
        }
    
    def mine_benchmark_results(
        self,
        benchmark_name: str,
        results: List[Dict[str, Any]]
    ) -> List[KnowledgeItem]:
        """
        Mine patterns from benchmark results.
        
        Args:
            benchmark_name: Name of benchmark (humaneval, mbpp, etc.)
            results: List of benchmark results with solutions
            
        Returns:
            Knowledge items extracted from successful solutions
        """
        items = []
        
        for result in results:
            if result.get("success", False):
                # Extract pattern from successful solution
                pattern = self._extract_pattern(result)
                
                if pattern:
                    item = KnowledgeItem.create(
                        source=IngestionSource.BENCHMARK_MINING,
                        knowledge_type=KnowledgeType.TEMPLATE,
                        content=pattern["content"],
                        context={
                            "benchmark": benchmark_name,
                            "problem_id": result.get("problem_id"),
                            "category": pattern.get("category")
                        },
                        domain="coding",
                        tags=[benchmark_name, pattern.get("category", "general")],
                        confidence=0.9,  # Verified by benchmark tests
                        evidence=[{"test_passed": True, "benchmark": benchmark_name}]
                    )
                    
                    # Track with Genesis Key
                    genesis_key = self.genesis_tracker.create_ingestion_key(
                        source=IngestionSource.BENCHMARK_MINING,
                        what=f"Mined pattern from {benchmark_name}",
                        input_data={"benchmark": benchmark_name, "problem_id": result.get("problem_id")},
                        output_data={"item_id": item.item_id, "category": pattern.get("category")},
                        tags=["benchmark", benchmark_name]
                    )
                    item.genesis_key_id = genesis_key
                    
                    items.append(item)
                    self.stats["patterns_extracted"] += 1
        
        self.stats["benchmarks_processed"] += 1
        return items
    
    def _extract_pattern(self, result: Dict[str, Any]) -> Optional[Dict]:
        """Extract reusable pattern from benchmark result."""
        solution = result.get("solution", "")
        prompt = result.get("prompt", "")
        
        if not solution:
            return None
        
        # Categorize the pattern
        category = self._categorize_solution(solution, prompt)
        
        return {
            "content": solution,
            "category": category,
            "prompt_type": self._classify_prompt(prompt)
        }
    
    def _categorize_solution(self, solution: str, prompt: str) -> str:
        """Categorize the solution pattern."""
        categories = {
            "sorting": ["sort", "sorted", "order"],
            "searching": ["find", "search", "index", "lookup"],
            "string_manipulation": ["split", "join", "replace", "strip"],
            "math": ["sum", "product", "factorial", "fibonacci"],
            "list_processing": ["filter", "map", "reduce", "comprehension"],
            "recursion": ["recursive", "base case"],
            "dynamic_programming": ["memo", "cache", "dp"],
            "graph": ["bfs", "dfs", "graph", "tree"]
        }
        
        solution_lower = solution.lower()
        
        for category, keywords in categories.items():
            if any(kw in solution_lower for kw in keywords):
                return category
        
        return "general"
    
    def _classify_prompt(self, prompt: str) -> str:
        """Classify the type of prompt."""
        prompt_lower = prompt.lower()
        
        if "return" in prompt_lower and "list" in prompt_lower:
            return "list_return"
        elif "return" in prompt_lower and ("true" in prompt_lower or "false" in prompt_lower):
            return "boolean_return"
        elif "return" in prompt_lower and "string" in prompt_lower:
            return "string_return"
        elif "return" in prompt_lower and ("int" in prompt_lower or "number" in prompt_lower):
            return "numeric_return"
        else:
            return "general"


# =============================================================================
# UNIFIED INGESTION PIPELINE
# =============================================================================

class UnifiedKnowledgeIngestion:
    """
    Unified pipeline that processes all knowledge sources.
    Normalizes, deduplicates, scores, and stores all knowledge.
    """
    
    def __init__(
        self,
        session=None,
        memory_mesh=None,
        learning_memory=None,
        llm_orchestrator=None
    ):
        self.session = session
        self.memory_mesh = memory_mesh
        self.learning_memory = learning_memory
        self.llm_orchestrator = llm_orchestrator
        
        # Genesis tracking
        self.genesis_tracker = GenesisKeyTracker(session)
        
        # Initialize all ingestion sources
        self.llm_requester = LLMKnowledgeRequester(llm_orchestrator, session)
        self.simulation_engine = SimulationEngine(session)
        self.replay_learner = ReplayLearner(session, learning_memory)
        self.self_distiller = SelfDistiller(session, learning_memory)
        self.multi_agent_debater = MultiAgentDebater(session, llm_orchestrator)
        self.benchmark_miner = BenchmarkMiner(session)
        
        # Deduplication cache
        self._content_hashes: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            "total_ingested": 0,
            "deduplicated": 0,
            "by_source": {},
            "by_type": {}
        }
    
    async def ingest(self, item: KnowledgeItem) -> IngestionResult:
        """
        Ingest a single knowledge item through the unified pipeline.
        
        Pipeline stages:
        1. Normalize
        2. Deduplicate
        3. Score quality
        4. Extract patterns
        5. Store with provenance
        """
        # 1. Normalize
        item = self._normalize(item)
        
        # 2. Check for duplicates
        content_hash = hashlib.sha256(item.content.encode()).hexdigest()
        if content_hash in self._content_hashes:
            self.stats["deduplicated"] += 1
            return IngestionResult(
                success=True,
                item_id=item.item_id,
                deduplicated=True,
                merged_with=self._content_hashes[content_hash]
            )
        
        # 3. Score quality
        item.quality_score = self._score_quality(item)
        item.trust_score = self._calculate_trust(item)
        
        # 4. Track with Genesis Key
        genesis_key = self.genesis_tracker.create_ingestion_key(
            source=item.source,
            what=f"Ingested {item.knowledge_type.value}: {item.content[:50]}...",
            input_data={
                "source": item.source.value,
                "type": item.knowledge_type.value,
                "content_length": len(item.content)
            },
            output_data={
                "item_id": item.item_id,
                "quality_score": item.quality_score,
                "trust_score": item.trust_score
            },
            tags=[item.source.value, item.knowledge_type.value] + item.tags[:5]
        )
        item.genesis_key_id = genesis_key
        item.ingested_at = datetime.utcnow()
        
        # 5. Store
        stored_as = await self._store(item)
        
        # Update caches and stats
        self._content_hashes[content_hash] = item.item_id
        self.stats["total_ingested"] += 1
        self.stats["by_source"][item.source.value] = self.stats["by_source"].get(item.source.value, 0) + 1
        self.stats["by_type"][item.knowledge_type.value] = self.stats["by_type"].get(item.knowledge_type.value, 0) + 1
        
        return IngestionResult(
            success=True,
            item_id=item.item_id,
            genesis_key_id=genesis_key,
            stored_as=stored_as,
            trust_score=item.trust_score
        )
    
    async def ingest_batch(self, items: List[KnowledgeItem]) -> List[IngestionResult]:
        """Ingest multiple items."""
        results = []
        for item in items:
            result = await self.ingest(item)
            results.append(result)
        return results
    
    def _normalize(self, item: KnowledgeItem) -> KnowledgeItem:
        """Normalize knowledge item."""
        # Clean content
        item.content = item.content.strip()
        
        # Ensure tags are lowercase
        item.tags = [t.lower() for t in item.tags]
        
        # Add source tag
        if item.source.value not in item.tags:
            item.tags.append(item.source.value)
        
        return item
    
    def _score_quality(self, item: KnowledgeItem) -> float:
        """Score the quality of a knowledge item."""
        score = 0.5
        
        # Content length (not too short, not too long)
        content_len = len(item.content)
        if 50 < content_len < 5000:
            score += 0.1
        elif content_len < 20:
            score -= 0.2
        
        # Has evidence
        if item.evidence:
            score += 0.15
        
        # Has context
        if item.context:
            score += 0.1
        
        # Source reliability
        reliable_sources = {
            IngestionSource.BENCHMARK_MINING: 0.15,
            IngestionSource.SELF_HEALING: 0.1,
            IngestionSource.SIMULATION_ENGINE: 0.1,
            IngestionSource.LLM_ON_REQUEST: 0.05
        }
        score += reliable_sources.get(item.source, 0)
        
        return min(1.0, max(0.0, score))
    
    def _calculate_trust(self, item: KnowledgeItem) -> float:
        """Calculate trust score for item."""
        # Base trust from source
        source_trust = {
            IngestionSource.BENCHMARK_MINING: 0.9,
            IngestionSource.SELF_HEALING: 0.8,
            IngestionSource.SIMULATION_ENGINE: 0.85,
            IngestionSource.REPLAY_LEARNING: 0.75,
            IngestionSource.SELF_DISTILLATION: 0.8,
            IngestionSource.MULTI_AGENT_DEBATE: 0.7,
            IngestionSource.LLM_ON_REQUEST: 0.6,
            IngestionSource.USER_FEEDBACK: 0.7,
            IngestionSource.FEDERATED_LEARNING: 0.65
        }
        
        base_trust = source_trust.get(item.source, 0.5)
        
        # Adjust by confidence
        trust = base_trust * 0.7 + item.confidence * 0.3
        
        # Boost for evidence
        if item.evidence:
            trust = min(1.0, trust + 0.1)
        
        return trust
    
    async def _store(self, item: KnowledgeItem) -> str:
        """Store knowledge item in appropriate memory system."""
        stored_as = "learning_memory"
        
        # Store in learning memory
        if self.learning_memory:
            try:
                if item.knowledge_type == KnowledgeType.PATTERN:
                    self.learning_memory.store_pattern({
                        "id": item.item_id,
                        "content": item.content,
                        "trust_score": item.trust_score,
                        "domain": item.domain,
                        "tags": item.tags,
                        "genesis_key_id": item.genesis_key_id
                    })
                    stored_as = "pattern"
                elif item.knowledge_type == KnowledgeType.PROCEDURE:
                    self.learning_memory.store_procedure({
                        "id": item.item_id,
                        "content": item.content,
                        "trust_score": item.trust_score,
                        "domain": item.domain,
                        "genesis_key_id": item.genesis_key_id
                    })
                    stored_as = "procedure"
                else:
                    self.learning_memory.store_example({
                        "id": item.item_id,
                        "type": item.knowledge_type.value,
                        "content": item.content,
                        "trust_score": item.trust_score,
                        "genesis_key_id": item.genesis_key_id
                    })
            except Exception as e:
                logger.warning(f"Failed to store in learning memory: {e}")
        
        # Also store in memory mesh for retrieval
        if self.memory_mesh:
            try:
                self.memory_mesh.store_knowledge(item.item_id, item.content, item.context)
            except Exception as e:
                logger.warning(f"Failed to store in memory mesh: {e}")
        
        return stored_as
    
    # =========================================================================
    # HIGH-LEVEL INGESTION METHODS
    # =========================================================================
    
    async def request_llm_knowledge(
        self,
        topic: str,
        template: str = "explain_concept",
        **kwargs
    ) -> List[IngestionResult]:
        """Request and ingest knowledge from LLM."""
        items = await self.llm_requester.request_knowledge(topic, template, **kwargs)
        return await self.ingest_batch(items)
    
    def generate_simulations(
        self,
        scenario_type: str,
        count: int = 5,
        **kwargs
    ) -> List[IngestionResult]:
        """Generate and ingest simulation scenarios."""
        items = self.simulation_engine.generate_scenario(scenario_type, count=count, **kwargs)
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.ingest_batch(items))
    
    def record_failure(self, task: Dict, attempt: Dict, error: str, context: Dict = None):
        """Record a failure for replay learning."""
        self.replay_learner.record_failure(task, attempt, error, context)
    
    def replay_and_learn(self, count: int = 10) -> List[IngestionResult]:
        """Replay failures and ingest learnings."""
        items = self.replay_learner.replay_failures(count)
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.ingest_batch(items))
    
    def distill_knowledge(self, domain: str = None) -> List[IngestionResult]:
        """Distill and compress existing knowledge."""
        items = self.self_distiller.distill_patterns(domain)
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.ingest_batch(items))
    
    async def debate_and_learn(self, topic: str, domain: str = None) -> List[IngestionResult]:
        """Run debate and ingest conclusions."""
        items = await self.multi_agent_debater.debate_topic(topic, domain=domain)
        return await self.ingest_batch(items)
    
    def mine_benchmarks(self, benchmark_name: str, results: List[Dict]) -> List[IngestionResult]:
        """Mine patterns from benchmark results."""
        items = self.benchmark_miner.mine_benchmark_results(benchmark_name, results)
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.ingest_batch(items))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive ingestion statistics."""
        return {
            "pipeline_stats": self.stats,
            "llm_requester": self.llm_requester.stats,
            "simulation_engine": self.simulation_engine.stats,
            "replay_learner": self.replay_learner.stats,
            "self_distiller": self.self_distiller.stats,
            "multi_agent_debater": self.multi_agent_debater.stats,
            "benchmark_miner": self.benchmark_miner.stats
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_unified_ingestion(session=None, **kwargs) -> UnifiedKnowledgeIngestion:
    """Factory function to create unified ingestion system."""
    return UnifiedKnowledgeIngestion(session=session, **kwargs)
