"""
LLM Interaction Observatory - Log, Analyze, and Learn from LLM Interactions

Captures ALL LLM inputs/outputs with Genesis Key tracking to:
1. Reverse engineer WHY the LLM responded a certain way
2. Query and analyze responses using OODA loop
3. Use interactions as training dataset
4. Track reasoning chains and decision patterns

Every LLM call becomes a learning opportunity.
"""

import logging
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class InteractionType(str, Enum):
    """Types of LLM interactions."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    EXPLANATION = "explanation"
    REASONING = "reasoning"
    PLANNING = "planning"
    QUESTION_ANSWER = "question_answer"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    CREATIVE = "creative"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class ResponseQuality(str, Enum):
    """Quality assessment of LLM response."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class LLMInteraction:
    """
    A single LLM interaction with full provenance.
    This is the core data structure for the observatory.
    """
    interaction_id: str
    
    # Input
    prompt: str
    system_prompt: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    input_tokens: int = 0
    
    # Output
    response: str = ""
    output_tokens: int = 0
    
    # Model info
    model_name: str = "unknown"
    model_provider: str = "unknown"
    temperature: float = 0.0
    max_tokens: int = 0
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    latency_ms: int = 0
    
    # Classification
    interaction_type: InteractionType = InteractionType.UNKNOWN
    domain: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Quality assessment
    quality: ResponseQuality = ResponseQuality.UNKNOWN
    quality_score: float = 0.0
    quality_reasons: List[str] = field(default_factory=list)
    
    # OODA Analysis
    ooda_observe: Dict[str, Any] = field(default_factory=dict)
    ooda_orient: Dict[str, Any] = field(default_factory=dict)
    ooda_decide: Dict[str, Any] = field(default_factory=dict)
    ooda_act: Dict[str, Any] = field(default_factory=dict)
    
    # Provenance
    genesis_key_id: Optional[str] = None
    parent_interaction_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Extracted patterns
    patterns_identified: List[str] = field(default_factory=list)
    reasoning_chain: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @staticmethod
    def create(prompt: str, **kwargs) -> "LLMInteraction":
        """Factory method to create an interaction."""
        return LLMInteraction(
            interaction_id=f"LLM-{uuid.uuid4().hex[:12]}",
            prompt=prompt,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "interaction_id": self.interaction_id,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "response": self.response,
            "model_name": self.model_name,
            "interaction_type": self.interaction_type.value,
            "quality": self.quality.value,
            "quality_score": self.quality_score,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "genesis_key_id": self.genesis_key_id,
            "started_at": self.started_at.isoformat(),
            "ooda": {
                "observe": self.ooda_observe,
                "orient": self.ooda_orient,
                "decide": self.ooda_decide,
                "act": self.ooda_act
            },
            "patterns_identified": self.patterns_identified,
            "reasoning_chain": self.reasoning_chain,
            "key_decisions": self.key_decisions
        }


@dataclass
class OODAAnalysis:
    """OODA loop analysis of an LLM interaction."""
    interaction_id: str
    
    # OBSERVE - What did the LLM see/receive?
    observe: Dict[str, Any] = field(default_factory=lambda: {
        "prompt_type": None,
        "prompt_length": 0,
        "key_entities": [],
        "constraints_given": [],
        "context_provided": [],
        "examples_given": 0,
        "task_clarity": 0.0
    })
    
    # ORIENT - How did it interpret the situation?
    orient: Dict[str, Any] = field(default_factory=lambda: {
        "inferred_intent": None,
        "domain_identified": None,
        "complexity_assessed": None,
        "similar_patterns": [],
        "knowledge_accessed": [],
        "assumptions_made": []
    })
    
    # DECIDE - What approach did it choose?
    decide: Dict[str, Any] = field(default_factory=lambda: {
        "strategy_chosen": None,
        "alternatives_considered": [],
        "risk_level": None,
        "confidence_level": 0.0,
        "constraints_applied": [],
        "trade_offs": []
    })
    
    # ACT - What did it produce?
    act: Dict[str, Any] = field(default_factory=lambda: {
        "response_type": None,
        "response_length": 0,
        "code_generated": False,
        "explanation_given": False,
        "caveats_mentioned": [],
        "follow_up_suggested": False
    })
    
    # Meta-analysis
    reasoning_quality: float = 0.0
    coherence_score: float = 0.0
    relevance_score: float = 0.0
    
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# GENESIS KEY INTEGRATION
# =============================================================================

class LLMGenesisTracker:
    """Track all LLM interactions with Genesis Keys."""
    
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
    
    def create_interaction_key(
        self,
        interaction: LLMInteraction,
        operation: str = "llm_call"
    ) -> Optional[str]:
        """Create a Genesis Key for an LLM interaction."""
        if not self.genesis_service:
            return None
        
        try:
            from models.genesis_key_models import GenesisKeyType
            
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.LLM_INTERACTION,
                what_description=f"LLM {operation}: {interaction.interaction_type.value}",
                who_actor=f"llm/{interaction.model_name}",
                where_location="cognitive/llm_interaction_observatory",
                why_reason=f"Processing {interaction.interaction_type.value} request",
                how_method=interaction.model_provider,
                input_data={
                    "prompt_hash": hashlib.sha256(interaction.prompt.encode()).hexdigest()[:16],
                    "prompt_length": len(interaction.prompt),
                    "system_prompt_length": len(interaction.system_prompt or ""),
                    "model": interaction.model_name,
                    "temperature": interaction.temperature,
                    "interaction_type": interaction.interaction_type.value
                },
                output_data={
                    "response_hash": hashlib.sha256(interaction.response.encode()).hexdigest()[:16],
                    "response_length": len(interaction.response),
                    "latency_ms": interaction.latency_ms,
                    "input_tokens": interaction.input_tokens,
                    "output_tokens": interaction.output_tokens,
                    "quality": interaction.quality.value,
                    "quality_score": interaction.quality_score
                },
                tags=[
                    "llm_interaction",
                    interaction.interaction_type.value,
                    interaction.model_name,
                    interaction.quality.value
                ],
                session=self.session
            )
            return key.key_id if key else None
        except Exception as e:
            logger.warning(f"Failed to create Genesis Key: {e}")
            return None


# =============================================================================
# INTERACTION ANALYZER
# =============================================================================

class InteractionAnalyzer:
    """
    Analyze LLM interactions to understand WHY responses were generated.
    Uses OODA loop framework for structured analysis.
    """
    
    def __init__(self, llm_orchestrator=None):
        self.llm_orchestrator = llm_orchestrator
        
        # Pattern matchers
        self.code_patterns = [
            r"```[\w]*\n",  # Code blocks
            r"def \w+\(",   # Function definitions
            r"class \w+:",  # Class definitions
            r"import \w+",  # Imports
        ]
        
        self.reasoning_indicators = [
            "because", "therefore", "since", "due to",
            "as a result", "consequently", "thus", "hence",
            "this means", "in order to", "the reason"
        ]
        
        self.decision_indicators = [
            "i recommend", "you should", "the best approach",
            "i suggest", "consider", "prefer", "choose",
            "the solution is", "here's how"
        ]
    
    def analyze_interaction(self, interaction: LLMInteraction) -> OODAAnalysis:
        """
        Perform full OODA analysis on an interaction.
        """
        analysis = OODAAnalysis(interaction_id=interaction.interaction_id)
        
        # OBSERVE - Analyze the input
        analysis.observe = self._analyze_observe(interaction)
        
        # ORIENT - Understand interpretation
        analysis.orient = self._analyze_orient(interaction)
        
        # DECIDE - Identify decisions made
        analysis.decide = self._analyze_decide(interaction)
        
        # ACT - Analyze the output
        analysis.act = self._analyze_act(interaction)
        
        # Calculate quality scores
        analysis.reasoning_quality = self._score_reasoning(interaction)
        analysis.coherence_score = self._score_coherence(interaction)
        analysis.relevance_score = self._score_relevance(interaction)
        
        # Update interaction with analysis
        interaction.ooda_observe = analysis.observe
        interaction.ooda_orient = analysis.orient
        interaction.ooda_decide = analysis.decide
        interaction.ooda_act = analysis.act
        
        return analysis
    
    def _analyze_observe(self, interaction: LLMInteraction) -> Dict[str, Any]:
        """Analyze what the LLM observed (input analysis)."""
        prompt = interaction.prompt
        
        # Detect prompt type
        prompt_type = self._classify_prompt(prompt)
        
        # Extract key entities
        entities = self._extract_entities(prompt)
        
        # Identify constraints
        constraints = self._extract_constraints(prompt)
        
        # Count examples
        examples = len(re.findall(r"example|e\.g\.|for instance", prompt.lower()))
        
        # Assess task clarity
        clarity = self._assess_clarity(prompt)
        
        return {
            "prompt_type": prompt_type,
            "prompt_length": len(prompt),
            "word_count": len(prompt.split()),
            "key_entities": entities,
            "constraints_given": constraints,
            "context_provided": list(interaction.context.keys()),
            "examples_given": examples,
            "task_clarity": clarity,
            "has_system_prompt": bool(interaction.system_prompt)
        }
    
    def _analyze_orient(self, interaction: LLMInteraction) -> Dict[str, Any]:
        """Analyze how the LLM interpreted the situation."""
        response = interaction.response
        
        # Infer what the LLM understood as the intent
        inferred_intent = self._infer_intent(interaction.prompt, response)
        
        # Identify domain
        domain = self._identify_domain(interaction.prompt, response)
        
        # Assess complexity
        complexity = self._assess_complexity(response)
        
        # Identify assumptions (explicit or implicit)
        assumptions = self._extract_assumptions(response)
        
        return {
            "inferred_intent": inferred_intent,
            "domain_identified": domain,
            "complexity_assessed": complexity,
            "similar_patterns": [],
            "knowledge_accessed": self._identify_knowledge_areas(response),
            "assumptions_made": assumptions
        }
    
    def _analyze_decide(self, interaction: LLMInteraction) -> Dict[str, Any]:
        """Analyze what decisions/approach the LLM chose."""
        response = interaction.response
        
        # Identify strategy
        strategy = self._identify_strategy(response)
        
        # Find alternatives mentioned
        alternatives = self._extract_alternatives(response)
        
        # Assess confidence
        confidence = self._assess_confidence(response)
        
        # Find trade-offs mentioned
        trade_offs = self._extract_trade_offs(response)
        
        return {
            "strategy_chosen": strategy,
            "alternatives_considered": alternatives,
            "risk_level": self._assess_risk_level(response),
            "confidence_level": confidence,
            "constraints_applied": self._extract_applied_constraints(response),
            "trade_offs": trade_offs
        }
    
    def _analyze_act(self, interaction: LLMInteraction) -> Dict[str, Any]:
        """Analyze the output/action taken."""
        response = interaction.response
        
        # Detect response type
        response_type = self._classify_response(response)
        
        # Check for code
        has_code = any(re.search(p, response) for p in self.code_patterns)
        
        # Check for explanation
        has_explanation = len([w for w in self.reasoning_indicators if w in response.lower()]) > 2
        
        # Find caveats
        caveats = self._extract_caveats(response)
        
        # Check for follow-up suggestions
        follow_up = any(phrase in response.lower() for phrase in [
            "you might also", "consider also", "next step",
            "alternatively", "keep in mind", "note that"
        ])
        
        return {
            "response_type": response_type,
            "response_length": len(response),
            "word_count": len(response.split()),
            "code_generated": has_code,
            "code_blocks": len(re.findall(r"```", response)) // 2,
            "explanation_given": has_explanation,
            "caveats_mentioned": caveats,
            "follow_up_suggested": follow_up,
            "lists_used": response.count("\n- ") + response.count("\n* ")
        }
    
    # Helper methods
    
    def _classify_prompt(self, prompt: str) -> str:
        """Classify the type of prompt."""
        prompt_lower = prompt.lower()
        
        if any(w in prompt_lower for w in ["write", "create", "generate", "implement"]):
            if "code" in prompt_lower or "function" in prompt_lower:
                return "code_generation"
            return "creation"
        elif any(w in prompt_lower for w in ["fix", "debug", "error", "bug"]):
            return "debugging"
        elif any(w in prompt_lower for w in ["explain", "what is", "how does", "why"]):
            return "explanation"
        elif any(w in prompt_lower for w in ["review", "check", "analyze"]):
            return "review"
        elif any(w in prompt_lower for w in ["refactor", "improve", "optimize"]):
            return "refactoring"
        elif any(w in prompt_lower for w in ["test", "spec", "unit test"]):
            return "testing"
        elif any(w in prompt_lower for w in ["plan", "design", "architect"]):
            return "planning"
        else:
            return "general"
    
    def _classify_response(self, response: str) -> str:
        """Classify the type of response."""
        if "```" in response:
            return "code_with_explanation"
        elif response.count("\n- ") > 3 or response.count("\n* ") > 3:
            return "list"
        elif response.count("\n") > 10:
            return "detailed_explanation"
        elif len(response) < 200:
            return "brief_answer"
        else:
            return "explanation"
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract key entities from text."""
        entities = []
        
        # Find capitalized words (potential names/entities)
        capitals = re.findall(r'\b[A-Z][a-zA-Z]+\b', text)
        entities.extend(capitals[:10])
        
        # Find quoted strings
        quoted = re.findall(r'"([^"]+)"', text)
        entities.extend(quoted[:5])
        
        # Find code identifiers
        code_ids = re.findall(r'`([^`]+)`', text)
        entities.extend(code_ids[:5])
        
        return list(set(entities))
    
    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints from prompt."""
        constraints = []
        
        constraint_phrases = [
            "must", "should", "need to", "required",
            "don't", "avoid", "without", "only",
            "limit", "maximum", "minimum", "at least"
        ]
        
        sentences = text.split(".")
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in constraint_phrases):
                constraints.append(sentence.strip())
        
        return constraints[:5]
    
    def _assess_clarity(self, prompt: str) -> float:
        """Assess how clear the prompt is."""
        score = 0.5
        
        # Longer prompts tend to be clearer
        if len(prompt) > 100:
            score += 0.1
        if len(prompt) > 300:
            score += 0.1
        
        # Presence of examples helps
        if "example" in prompt.lower():
            score += 0.1
        
        # Clear structure (lists, bullets)
        if "\n-" in prompt or "\n*" in prompt:
            score += 0.1
        
        # Question marks indicate clear questions
        if "?" in prompt:
            score += 0.05
        
        return min(1.0, score)
    
    def _infer_intent(self, prompt: str, response: str) -> str:
        """Infer the user's intent from prompt and response."""
        prompt_lower = prompt.lower()
        
        if "how" in prompt_lower and "?" in prompt:
            return "seeking_instructions"
        elif "why" in prompt_lower:
            return "seeking_explanation"
        elif "what" in prompt_lower and "?" in prompt:
            return "seeking_information"
        elif any(w in prompt_lower for w in ["write", "create", "generate"]):
            return "requesting_creation"
        elif any(w in prompt_lower for w in ["fix", "debug"]):
            return "requesting_fix"
        elif any(w in prompt_lower for w in ["review", "check"]):
            return "requesting_review"
        else:
            return "general_request"
    
    def _identify_domain(self, prompt: str, response: str) -> str:
        """Identify the domain of the interaction."""
        combined = (prompt + " " + response).lower()
        
        domain_keywords = {
            "python": ["python", "def ", "import ", "pip"],
            "javascript": ["javascript", "js", "node", "npm", "const "],
            "database": ["sql", "database", "query", "table", "index"],
            "web": ["html", "css", "http", "api", "rest"],
            "devops": ["docker", "kubernetes", "ci/cd", "deploy"],
            "security": ["security", "auth", "encrypt", "token"],
            "testing": ["test", "assert", "mock", "fixture"],
            "architecture": ["design", "pattern", "architecture", "system"]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in combined for kw in keywords):
                return domain
        
        return "general"
    
    def _assess_complexity(self, response: str) -> str:
        """Assess the complexity of the response."""
        word_count = len(response.split())
        code_blocks = len(re.findall(r"```", response)) // 2
        
        if word_count > 500 or code_blocks > 3:
            return "high"
        elif word_count > 200 or code_blocks > 1:
            return "medium"
        else:
            return "low"
    
    def _extract_assumptions(self, response: str) -> List[str]:
        """Extract assumptions from response."""
        assumptions = []
        
        assumption_phrases = [
            "assuming", "i assume", "if you", "provided that",
            "given that", "since you", "based on"
        ]
        
        sentences = response.split(".")
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in assumption_phrases):
                assumptions.append(sentence.strip())
        
        return assumptions[:5]
    
    def _identify_knowledge_areas(self, response: str) -> List[str]:
        """Identify knowledge areas accessed in response."""
        areas = []
        
        knowledge_indicators = {
            "programming_concepts": ["function", "class", "method", "variable"],
            "algorithms": ["algorithm", "complexity", "O(n)", "sort", "search"],
            "best_practices": ["best practice", "recommended", "convention"],
            "security": ["security", "vulnerability", "injection", "sanitize"],
            "performance": ["performance", "optimize", "efficient", "cache"]
        }
        
        response_lower = response.lower()
        for area, indicators in knowledge_indicators.items():
            if any(ind in response_lower for ind in indicators):
                areas.append(area)
        
        return areas
    
    def _identify_strategy(self, response: str) -> str:
        """Identify the strategy used in the response."""
        response_lower = response.lower()
        
        if "step by step" in response_lower or "first" in response_lower and "then" in response_lower:
            return "step_by_step"
        elif "here's" in response_lower and "```" in response:
            return "direct_solution"
        elif "let me explain" in response_lower:
            return "explanation_first"
        elif "there are several" in response_lower or "options" in response_lower:
            return "comparative"
        else:
            return "direct"
    
    def _extract_alternatives(self, response: str) -> List[str]:
        """Extract alternatives mentioned in response."""
        alternatives = []
        
        alt_phrases = [
            "alternatively", "another approach", "you could also",
            "another option", "or you could", "instead of"
        ]
        
        sentences = response.split(".")
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in alt_phrases):
                alternatives.append(sentence.strip())
        
        return alternatives[:3]
    
    def _assess_confidence(self, response: str) -> float:
        """Assess the confidence level in the response."""
        response_lower = response.lower()
        
        high_confidence = ["definitely", "certainly", "clearly", "obviously", "must"]
        low_confidence = ["might", "maybe", "perhaps", "could", "possibly", "i think"]
        
        high_count = sum(1 for word in high_confidence if word in response_lower)
        low_count = sum(1 for word in low_confidence if word in response_lower)
        
        if high_count > low_count:
            return 0.8 + min(0.2, high_count * 0.05)
        elif low_count > high_count:
            return 0.5 - min(0.2, low_count * 0.05)
        else:
            return 0.6
    
    def _assess_risk_level(self, response: str) -> str:
        """Assess risk level mentioned in response."""
        response_lower = response.lower()
        
        high_risk_words = ["careful", "warning", "caution", "dangerous", "risk", "security"]
        if any(word in response_lower for word in high_risk_words):
            return "high"
        
        medium_risk_words = ["consider", "note that", "keep in mind"]
        if any(word in response_lower for word in medium_risk_words):
            return "medium"
        
        return "low"
    
    def _extract_applied_constraints(self, response: str) -> List[str]:
        """Extract constraints that were applied in the response."""
        constraints = []
        
        # Look for "I used/applied/followed" patterns
        patterns = [
            r"I (?:used|applied|followed) (\w+)",
            r"using (\w+ pattern)",
            r"following (\w+ principles)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            constraints.extend(matches)
        
        return constraints[:5]
    
    def _extract_trade_offs(self, response: str) -> List[str]:
        """Extract trade-offs mentioned in response."""
        trade_offs = []
        
        trade_off_phrases = [
            "trade-off", "tradeoff", "however", "but",
            "on the other hand", "downside", "drawback"
        ]
        
        sentences = response.split(".")
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in trade_off_phrases):
                trade_offs.append(sentence.strip())
        
        return trade_offs[:3]
    
    def _extract_caveats(self, response: str) -> List[str]:
        """Extract caveats mentioned in response."""
        caveats = []
        
        caveat_phrases = [
            "note that", "keep in mind", "be aware",
            "caveat", "warning", "important"
        ]
        
        sentences = response.split(".")
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in caveat_phrases):
                caveats.append(sentence.strip())
        
        return caveats[:3]
    
    def _score_reasoning(self, interaction: LLMInteraction) -> float:
        """Score the quality of reasoning in the response."""
        response = interaction.response.lower()
        
        score = 0.5
        
        # Check for reasoning indicators
        reasoning_count = sum(1 for word in self.reasoning_indicators if word in response)
        score += min(0.3, reasoning_count * 0.05)
        
        # Check for structured response
        if "1." in interaction.response or "step" in response:
            score += 0.1
        
        # Check for examples
        if "example" in response or "for instance" in response:
            score += 0.1
        
        return min(1.0, score)
    
    def _score_coherence(self, interaction: LLMInteraction) -> float:
        """Score the coherence of the response."""
        response = interaction.response
        
        # Simple heuristics
        score = 0.7
        
        # Check paragraph structure
        paragraphs = response.split("\n\n")
        if 2 <= len(paragraphs) <= 10:
            score += 0.1
        
        # Check sentence length consistency
        sentences = response.split(".")
        if sentences:
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if lengths:
                avg = sum(lengths) / len(lengths)
                if 10 <= avg <= 30:
                    score += 0.1
        
        return min(1.0, score)
    
    def _score_relevance(self, interaction: LLMInteraction) -> float:
        """Score how relevant the response is to the prompt."""
        prompt_words = set(interaction.prompt.lower().split())
        response_words = set(interaction.response.lower().split())
        
        # Calculate word overlap
        common_words = prompt_words & response_words
        
        # Filter out common stopwords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of", "and", "or"}
        meaningful_common = common_words - stopwords
        meaningful_prompt = prompt_words - stopwords
        
        if not meaningful_prompt:
            return 0.5
        
        overlap_ratio = len(meaningful_common) / len(meaningful_prompt)
        
        return min(1.0, 0.5 + overlap_ratio * 0.5)
    
    def extract_reasoning_chain(self, interaction: LLMInteraction) -> List[str]:
        """Extract the reasoning chain from response."""
        response = interaction.response
        chain = []
        
        # Look for step-by-step reasoning
        step_pattern = r"(?:step \d+|first|second|third|then|next|finally)[:\s]+([^.]+)"
        steps = re.findall(step_pattern, response, re.IGNORECASE)
        chain.extend(steps)
        
        # Look for because/therefore chains
        reason_pattern = r"(?:because|therefore|thus|since)[:\s]+([^.]+)"
        reasons = re.findall(reason_pattern, response, re.IGNORECASE)
        chain.extend(reasons)
        
        interaction.reasoning_chain = chain[:10]
        return chain[:10]
    
    def extract_key_decisions(self, interaction: LLMInteraction) -> List[str]:
        """Extract key decisions from response."""
        response = interaction.response
        decisions = []
        
        for indicator in self.decision_indicators:
            pattern = rf"{indicator}[:\s]+([^.]+)"
            matches = re.findall(pattern, response, re.IGNORECASE)
            decisions.extend(matches)
        
        interaction.key_decisions = decisions[:5]
        return decisions[:5]


# =============================================================================
# INTERACTION REPOSITORY
# =============================================================================

class InteractionRepository:
    """
    Store and query LLM interactions.
    This becomes the training dataset.
    """
    
    def __init__(self, storage_path: Optional[Path] = None, session=None):
        self.storage_path = storage_path or Path("data/llm_interactions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.session = session
        
        # In-memory index for fast queries
        self._interactions: Dict[str, LLMInteraction] = {}
        self._by_type: Dict[str, List[str]] = {}
        self._by_quality: Dict[str, List[str]] = {}
        self._by_domain: Dict[str, List[str]] = {}
        
        # Load existing interactions
        self._load_interactions()
    
    def _load_interactions(self):
        """Load interactions from disk."""
        try:
            index_file = self.storage_path / "index.json"
            if index_file.exists():
                with open(index_file) as f:
                    data = json.load(f)
                    logger.info(f"Loaded {len(data.get('interactions', {}))} interactions from index")
        except Exception as e:
            logger.warning(f"Failed to load interactions: {e}")
    
    def store(self, interaction: LLMInteraction):
        """Store an interaction."""
        self._interactions[interaction.interaction_id] = interaction
        
        # Index by type
        type_key = interaction.interaction_type.value
        if type_key not in self._by_type:
            self._by_type[type_key] = []
        self._by_type[type_key].append(interaction.interaction_id)
        
        # Index by quality
        quality_key = interaction.quality.value
        if quality_key not in self._by_quality:
            self._by_quality[quality_key] = []
        self._by_quality[quality_key].append(interaction.interaction_id)
        
        # Index by domain
        if interaction.domain:
            if interaction.domain not in self._by_domain:
                self._by_domain[interaction.domain] = []
            self._by_domain[interaction.domain].append(interaction.interaction_id)
        
        # Persist to disk
        self._persist_interaction(interaction)
    
    def _persist_interaction(self, interaction: LLMInteraction):
        """Persist interaction to disk."""
        try:
            file_path = self.storage_path / f"{interaction.interaction_id}.json"
            with open(file_path, "w") as f:
                json.dump(interaction.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist interaction: {e}")
    
    def get(self, interaction_id: str) -> Optional[LLMInteraction]:
        """Get interaction by ID."""
        return self._interactions.get(interaction_id)
    
    def query(
        self,
        interaction_type: Optional[InteractionType] = None,
        quality: Optional[ResponseQuality] = None,
        domain: Optional[str] = None,
        min_quality_score: float = 0.0,
        limit: int = 100
    ) -> List[LLMInteraction]:
        """Query interactions with filters."""
        candidates = set(self._interactions.keys())
        
        if interaction_type:
            type_ids = set(self._by_type.get(interaction_type.value, []))
            candidates &= type_ids
        
        if quality:
            quality_ids = set(self._by_quality.get(quality.value, []))
            candidates &= quality_ids
        
        if domain:
            domain_ids = set(self._by_domain.get(domain, []))
            candidates &= domain_ids
        
        results = []
        for iid in candidates:
            interaction = self._interactions.get(iid)
            if interaction and interaction.quality_score >= min_quality_score:
                results.append(interaction)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_training_dataset(
        self,
        min_quality: ResponseQuality = ResponseQuality.GOOD,
        domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get interactions as training dataset.
        Returns prompt/response pairs with metadata.
        """
        quality_order = [
            ResponseQuality.EXCELLENT,
            ResponseQuality.GOOD,
            ResponseQuality.ACCEPTABLE
        ]
        
        min_index = quality_order.index(min_quality) if min_quality in quality_order else 2
        acceptable_qualities = quality_order[:min_index + 1]
        
        dataset = []
        for interaction in self._interactions.values():
            if interaction.quality not in acceptable_qualities:
                continue
            if domains and interaction.domain not in domains:
                continue
            
            dataset.append({
                "prompt": interaction.prompt,
                "response": interaction.response,
                "system_prompt": interaction.system_prompt,
                "interaction_type": interaction.interaction_type.value,
                "domain": interaction.domain,
                "quality_score": interaction.quality_score,
                "ooda_analysis": {
                    "observe": interaction.ooda_observe,
                    "orient": interaction.ooda_orient,
                    "decide": interaction.ooda_decide,
                    "act": interaction.ooda_act
                },
                "reasoning_chain": interaction.reasoning_chain,
                "key_decisions": interaction.key_decisions,
                "genesis_key_id": interaction.genesis_key_id
            })
        
        return dataset
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics."""
        return {
            "total_interactions": len(self._interactions),
            "by_type": {k: len(v) for k, v in self._by_type.items()},
            "by_quality": {k: len(v) for k, v in self._by_quality.items()},
            "by_domain": {k: len(v) for k, v in self._by_domain.items()}
        }


# =============================================================================
# LLM INTERACTION OBSERVATORY (Main Class)
# =============================================================================

class LLMInteractionObservatory:
    """
    Main observatory class that captures, analyzes, and learns from LLM interactions.
    
    Usage:
        observatory = LLMInteractionObservatory()
        
        # Wrap LLM call
        interaction = observatory.observe_call(prompt, response, model="gpt-4")
        
        # Query why a response was generated
        analysis = observatory.query_why(interaction.interaction_id)
        
        # Get training dataset
        dataset = observatory.get_training_data()
    """
    
    def __init__(
        self,
        session=None,
        storage_path: Optional[Path] = None,
        llm_orchestrator=None
    ):
        self.session = session
        self.storage_path = storage_path or Path("data/llm_observatory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.genesis_tracker = LLMGenesisTracker(session)
        self.analyzer = InteractionAnalyzer(llm_orchestrator)
        self.repository = InteractionRepository(self.storage_path, session)
        
        # Statistics
        self.stats = {
            "total_observed": 0,
            "total_analyzed": 0,
            "by_type": {},
            "by_quality": {},
            "avg_quality_score": 0.0
        }
    
    def observe_call(
        self,
        prompt: str,
        response: str,
        model: str = "unknown",
        system_prompt: str = None,
        context: Dict[str, Any] = None,
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        **kwargs
    ) -> LLMInteraction:
        """
        Observe and record an LLM call.
        
        This is the main entry point - call this after every LLM interaction.
        """
        # Create interaction
        interaction = LLMInteraction.create(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context or {},
            response=response,
            model_name=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            **kwargs
        )
        interaction.completed_at = datetime.utcnow()
        
        # Classify interaction type
        interaction.interaction_type = self._classify_type(prompt, response)
        
        # Analyze with OODA
        analysis = self.analyzer.analyze_interaction(interaction)
        
        # Extract reasoning and decisions
        self.analyzer.extract_reasoning_chain(interaction)
        self.analyzer.extract_key_decisions(interaction)
        
        # Assess quality
        interaction.quality, interaction.quality_score = self._assess_quality(interaction, analysis)
        
        # Identify domain
        interaction.domain = analysis.orient.get("domain_identified", "general")
        
        # Create Genesis Key
        genesis_key = self.genesis_tracker.create_interaction_key(interaction)
        interaction.genesis_key_id = genesis_key
        
        # Store
        self.repository.store(interaction)
        
        # Update stats
        self._update_stats(interaction)
        
        logger.info(
            f"Observed LLM call: {interaction.interaction_id} "
            f"type={interaction.interaction_type.value} "
            f"quality={interaction.quality.value}"
        )
        
        return interaction
    
    def query_why(self, interaction_id: str) -> Dict[str, Any]:
        """
        Query WHY an LLM generated a specific response.
        
        Uses OODA analysis to explain the reasoning.
        """
        interaction = self.repository.get(interaction_id)
        if not interaction:
            return {"error": "Interaction not found"}
        
        return {
            "interaction_id": interaction_id,
            "question": "Why did the LLM respond this way?",
            "analysis": {
                "what_it_observed": {
                    "prompt_type": interaction.ooda_observe.get("prompt_type"),
                    "task_clarity": interaction.ooda_observe.get("task_clarity"),
                    "key_entities": interaction.ooda_observe.get("key_entities"),
                    "constraints": interaction.ooda_observe.get("constraints_given")
                },
                "how_it_interpreted": {
                    "inferred_intent": interaction.ooda_orient.get("inferred_intent"),
                    "domain": interaction.ooda_orient.get("domain_identified"),
                    "complexity": interaction.ooda_orient.get("complexity_assessed"),
                    "assumptions": interaction.ooda_orient.get("assumptions_made")
                },
                "what_it_decided": {
                    "strategy": interaction.ooda_decide.get("strategy_chosen"),
                    "confidence": interaction.ooda_decide.get("confidence_level"),
                    "alternatives": interaction.ooda_decide.get("alternatives_considered"),
                    "trade_offs": interaction.ooda_decide.get("trade_offs")
                },
                "what_it_produced": {
                    "response_type": interaction.ooda_act.get("response_type"),
                    "code_generated": interaction.ooda_act.get("code_generated"),
                    "explanation_given": interaction.ooda_act.get("explanation_given"),
                    "caveats": interaction.ooda_act.get("caveats_mentioned")
                }
            },
            "reasoning_chain": interaction.reasoning_chain,
            "key_decisions": interaction.key_decisions,
            "quality_assessment": {
                "quality": interaction.quality.value,
                "score": interaction.quality_score,
                "reasons": interaction.quality_reasons
            },
            "genesis_key": interaction.genesis_key_id
        }
    
    def query_by_output(self, output_fragment: str) -> List[Dict[str, Any]]:
        """Query interactions by output content."""
        results = []
        for interaction in self.repository._interactions.values():
            if output_fragment.lower() in interaction.response.lower():
                results.append({
                    "interaction_id": interaction.interaction_id,
                    "prompt_preview": interaction.prompt[:200],
                    "response_preview": interaction.response[:200],
                    "type": interaction.interaction_type.value,
                    "quality": interaction.quality.value,
                    "genesis_key": interaction.genesis_key_id
                })
        return results[:20]
    
    def get_training_data(
        self,
        min_quality: str = "good",
        domains: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get interactions as training dataset."""
        try:
            quality = ResponseQuality(min_quality)
        except ValueError:
            quality = ResponseQuality.GOOD
        
        return self.repository.get_training_dataset(min_quality=quality, domains=domains)
    
    def get_patterns(self, interaction_type: str = None) -> Dict[str, Any]:
        """Get patterns from observed interactions."""
        interactions = self.repository.query(
            interaction_type=InteractionType(interaction_type) if interaction_type else None,
            min_quality_score=0.7
        )
        
        patterns = {
            "strategies": {},
            "domains": {},
            "reasoning_patterns": [],
            "common_decisions": []
        }
        
        for i in interactions:
            # Count strategies
            strategy = i.ooda_decide.get("strategy_chosen", "unknown")
            patterns["strategies"][strategy] = patterns["strategies"].get(strategy, 0) + 1
            
            # Count domains
            domain = i.domain or "unknown"
            patterns["domains"][domain] = patterns["domains"].get(domain, 0) + 1
            
            # Collect reasoning patterns
            if i.reasoning_chain:
                patterns["reasoning_patterns"].extend(i.reasoning_chain[:3])
            
            # Collect decisions
            if i.key_decisions:
                patterns["common_decisions"].extend(i.key_decisions[:2])
        
        return patterns
    
    def _classify_type(self, prompt: str, response: str) -> InteractionType:
        """Classify the interaction type."""
        prompt_lower = prompt.lower()
        
        if any(w in prompt_lower for w in ["write code", "implement", "create function", "generate code"]):
            return InteractionType.CODE_GENERATION
        elif any(w in prompt_lower for w in ["fix", "debug", "error", "bug"]):
            return InteractionType.BUG_FIX
        elif any(w in prompt_lower for w in ["review", "check code"]):
            return InteractionType.CODE_REVIEW
        elif any(w in prompt_lower for w in ["explain", "what is", "how does"]):
            return InteractionType.EXPLANATION
        elif any(w in prompt_lower for w in ["plan", "design", "architect"]):
            return InteractionType.PLANNING
        elif any(w in prompt_lower for w in ["test", "spec"]):
            return InteractionType.TEST_GENERATION
        elif any(w in prompt_lower for w in ["refactor", "improve", "optimize"]):
            return InteractionType.REFACTORING
        elif any(w in prompt_lower for w in ["document", "docstring"]):
            return InteractionType.DOCUMENTATION
        elif "?" in prompt:
            return InteractionType.QUESTION_ANSWER
        else:
            return InteractionType.UNKNOWN
    
    def _assess_quality(
        self,
        interaction: LLMInteraction,
        analysis: OODAAnalysis
    ) -> Tuple[ResponseQuality, float]:
        """Assess the quality of the interaction."""
        score = 0.5
        reasons = []
        
        # Check reasoning quality
        if analysis.reasoning_quality > 0.7:
            score += 0.15
            reasons.append("Good reasoning")
        
        # Check coherence
        if analysis.coherence_score > 0.7:
            score += 0.1
            reasons.append("Coherent response")
        
        # Check relevance
        if analysis.relevance_score > 0.7:
            score += 0.15
            reasons.append("Relevant to prompt")
        
        # Check for code in code-related tasks
        if interaction.interaction_type in [InteractionType.CODE_GENERATION, InteractionType.BUG_FIX]:
            if interaction.ooda_act.get("code_generated"):
                score += 0.1
                reasons.append("Includes code")
        
        # Determine quality level
        if score >= 0.85:
            quality = ResponseQuality.EXCELLENT
        elif score >= 0.7:
            quality = ResponseQuality.GOOD
        elif score >= 0.5:
            quality = ResponseQuality.ACCEPTABLE
        elif score >= 0.3:
            quality = ResponseQuality.POOR
        else:
            quality = ResponseQuality.FAILED
        
        interaction.quality_reasons = reasons
        return quality, score
    
    def _update_stats(self, interaction: LLMInteraction):
        """Update observatory statistics."""
        self.stats["total_observed"] += 1
        self.stats["total_analyzed"] += 1
        
        type_key = interaction.interaction_type.value
        self.stats["by_type"][type_key] = self.stats["by_type"].get(type_key, 0) + 1
        
        quality_key = interaction.quality.value
        self.stats["by_quality"][quality_key] = self.stats["by_quality"].get(quality_key, 0) + 1
        
        # Update rolling average quality score
        total = self.stats["total_observed"]
        current_avg = self.stats["avg_quality_score"]
        self.stats["avg_quality_score"] = (current_avg * (total - 1) + interaction.quality_score) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get observatory statistics."""
        return {
            **self.stats,
            "repository": self.repository.get_stats()
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_observatory(session=None, **kwargs) -> LLMInteractionObservatory:
    """Factory function to create observatory."""
    return LLMInteractionObservatory(session=session, **kwargs)
