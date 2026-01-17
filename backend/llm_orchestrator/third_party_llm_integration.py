import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported third-party LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    CUSTOM = "custom"


@dataclass
class ThirdPartyLLMConfig:
    """Configuration for a third-party LLM."""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 60
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Integration settings
    enable_handshake: bool = True
    enable_hallucination_guard: bool = True
    enable_cognitive_enforcement: bool = True
    enable_layer1_validation: bool = True
    enable_genesis_tracking: bool = True


@dataclass
class HandshakeResult:
    """Result of LLM handshake."""
    success: bool
    llm_id: str
    provider: LLMProvider
    model_name: str
    handshake_timestamp: datetime
    system_context_provided: bool
    rules_acknowledged: bool
    integration_test_passed: bool
    capabilities: Dict[str, Any]
    errors: List[str] = field(default_factory=list)


class SystemContextProvider:
    """
    Provides complete system context for third-party LLM integration.
    
    Generates comprehensive handshake documentation including:
    - System architecture
    - Rules and governance
    - Available APIs
    - Integration protocols
    - Best practices
    """
    
    def __init__(self):
        self.context_cache: Dict[str, str] = {}
    
    def get_complete_system_context(self) -> str:
        """
        Generate complete system context for LLM handshake.
        
        Returns:
            Complete system documentation as string
        """
        if "complete_context" in self.context_cache:
            return self.context_cache["complete_context"]
        
        context = self._build_system_context()
        self.context_cache["complete_context"] = context
        return context
    
    def _build_system_context(self) -> str:
        """Build complete system context."""
        return f"""
# GRACE System Integration Guide
# Version: 3.1
# Date: {datetime.now().isoformat()}

## 🎯 Welcome to GRACE

You are integrating with GRACE (Generalized Reasoning and Cognitive Engine), an autonomous AI system with:
- Layer 1: Trust & Truth Foundation (Deterministic)
- Layer 2: Intelligent Processing (Neural/AI)
- Complete governance framework
- Hallucination prevention (6 layers)
- Genesis Key tracking (complete audit trail)

---

## 📋 SYSTEM ARCHITECTURE

### Layer 1: Trust & Truth Foundation (Deterministic)
- **Purpose**: Source of truth, prevents hallucinations
- **Location**: `learning_examples` table in database
- **Key Features**:
  - Trust scoring (mathematical, deterministic)
  - Source reliability tracking
  - Validation history
  - File provenance (SHA-256 hashing)
  - Complete audit trail

### Layer 2: Intelligent Processing (Neural/AI)
- **Purpose**: AI-powered tasks (embeddings, LLM orchestration, semantic understanding)
- **Key Features**:
  - Multi-LLM orchestration
  - RAG (Retrieval-Augmented Generation)
  - Semantic search
  - Neural embeddings

### Integration Rule: Layer 1 CONTROLS Layer 2
- All LLM outputs are validated against Layer 1
- Trust scores are calculated deterministically
- Decisions are evidence-based, not probabilistic

---

## 🛡️ HALLUCINATION PREVENTION (6 LAYERS)

You MUST follow these rules to prevent hallucinations:

### Layer 1: Repository Grounding
- **Rule**: All responses must reference actual files/documents
- **How**: Use `repo_access.read_file()`, `repo_access.search_code()`
- **Validation**: Response must cite specific file paths

### Layer 2: Cross-Model Consensus
- **Rule**: Multiple models must agree on response
- **How**: Your response will be compared with other LLMs
- **Validation**: Consensus score must be >= 0.7

### Layer 3: Contradiction Detection
- **Rule**: Response must not contradict existing knowledge
- **How**: Semantic contradiction detection against RAG system
- **Validation**: Contradiction score must be < 0.3

### Layer 4: Confidence Scoring
- **Rule**: Response must have high confidence
- **How**: Source reliability + Content quality + Consensus + Recency
- **Validation**: Confidence score must be >= 0.6

### Layer 5: Trust System Verification
- **Rule**: Response must align with Layer 1 knowledge
- **How**: Validated against high-trust learning examples
- **Validation**: Trust score must be >= 0.7

### Layer 6: External Verification
- **Rule**: Critical claims must be verifiable
- **How**: Checked against documentation/web sources
- **Validation**: External verification must pass

**CRITICAL**: If ANY layer fails, your response will be REJECTED and Layer 1 knowledge will be used instead.

---

## 🧠 COGNITIVE FRAMEWORK (OODA LOOP + 12 INVARIANTS)

You MUST follow GRACE's cognitive framework:

### OODA Loop (Observe → Orient → Decide → Act)
1. **Observe**: Gather all relevant information
2. **Orient**: Understand context and constraints
3. **Decide**: Choose best action based on evidence
4. **Act**: Execute with full traceability

### 12 Invariants (MANDATORY)
1. **OODA as Primary Control Loop** - Always follow OODA
2. **Explicit Ambiguity Accounting** - Mark known/inferred/assumed/unknown
3. **Reversibility Before Commitment** - Prefer reversible actions
4. **Determinism Where Safety Depends on It** - Critical paths are deterministic
5. **Blast Radius Minimization** - Assess impact scope (local/component/systemic)
6. **Observability Is Mandatory** - All decisions logged
7. **Simplicity Is First-Class** - Complexity must justify itself
8. **Feedback Is Continuous** - Outcomes feed back into system
9. **Bounded Recursion** - Recursion limits enforced (max depth: 3)
10. **Optionality > Optimization** - Preserve future choices
11. **Time-Bounded Reasoning** - Planning must terminate (max: 30 seconds)
12. **Forward Simulation** - Evaluate multiple paths before deciding

**CRITICAL**: Every response must acknowledge which invariants were considered.

---

## 📚 AVAILABLE APIs AND SCRIPTS

### Repository Access (Read-Only)
```python
# Access GRACE's codebase and knowledge
repo_access.read_file(file_path: str) -> str
repo_access.search_code(pattern: str) -> List[Dict]
repo_access.get_file_tree() -> Dict
repo_access.get_genesis_keys() -> List[Dict]
repo_access.get_learning_examples(min_trust_score: float) -> List[Dict]
repo_access.get_document(document_id: int) -> Dict
repo_access.get_document_chunks(document_id: int) -> List[Dict]
```

### Layer 1 Access (Trust System)
```python
# Query trusted knowledge
layer1.get_knowledge(topic: str, min_trust_score: float) -> Dict
layer1.validate_against_trust_system(content: str) -> Dict
layer1.calculate_trust_score(...) -> float
```

### Genesis Key System (Audit Trail)
```python
# Track all operations
genesis.create_genesis_key(
    what: str,
    when: datetime,
    who: str,
    why: str,
    how: str
) -> str
```

### Learning Memory
```python
# Access learning examples
learning_memory.get_examples(
    min_trust_score: float,
    topic: Optional[str]
) -> List[Dict]
```

---

## 🔐 GOVERNANCE RULES

### Three-Pillar Governance Framework

#### 1. Operational Governance
- **Rules**: System behavior rules
- **Enforcement**: Automatic validation
- **KPIs**: Performance metrics tracked

#### 2. Behavioral Governance
- **Rules**: AI behavior constraints
- **Enforcement**: Cognitive framework
- **KPIs**: Trust scores, validation rates

#### 3. Immutable Governance
- **Rules**: Cannot be changed without approval
- **Enforcement**: Human-in-the-loop review
- **KPIs**: Compliance tracking

**CRITICAL**: All responses must comply with governance rules.

---

## 📝 RESPONSE FORMAT REQUIREMENTS

### Required Fields
Every response MUST include:
1. **Content**: Your actual response
2. **Sources**: File paths/documents referenced
3. **Trust Score**: Confidence in response (0-1)
4. **Evidence**: Layer 1 evidence supporting response
5. **Invariants**: Which OODA invariants were considered
6. **Ambiguity Ledger**: Known/Inferred/Assumed/Unknown breakdown

### Example Response Format
```json
{{
    "content": "Your response here",
    "sources": [
        {{"file": "path/to/file.py", "line": 42, "trust": 0.85}}
    ],
    "trust_score": 0.82,
    "evidence": {{
        "layer1_knowledge": "Topic from learning_examples",
        "validation_history": {{"validated": 3, "invalidated": 0}},
        "source_reliability": 0.90
    }},
    "invariants_considered": [
        "OODA Loop",
        "Explicit Ambiguity Accounting",
        "Determinism Where Safety Depends on It"
    ],
    "ambiguity_ledger": {{
        "known": ["Fact 1", "Fact 2"],
        "inferred": ["Inference 1"],
        "assumed": ["Assumption 1"],
        "unknown": ["Unknown 1"]
    }}
}}
```

---

## ⚠️ CRITICAL RULES

### DO:
✅ Always cite sources (file paths, line numbers)
✅ Always provide trust scores
✅ Always acknowledge OODA invariants
✅ Always mark ambiguity (known/inferred/assumed/unknown)
✅ Always validate against Layer 1 when possible
✅ Always use repository access for code references
✅ Always provide evidence for claims

### DON'T:
❌ Never make up information
❌ Never cite non-existent files
❌ Never skip trust scoring
❌ Never ignore Layer 1 validation
❌ Never bypass hallucination prevention
❌ Never skip audit trail (Genesis Keys)
❌ Never ignore governance rules

---

## 🔄 INTEGRATION PROTOCOL

### Step 1: Handshake
When you connect, you will receive this complete system context.

### Step 2: Acknowledgment
You must acknowledge:
- Understanding of system architecture
- Agreement to follow all rules
- Capability to provide required response format

### Step 3: Integration Test
You will be tested with a sample query to verify:
- Response format compliance
- Source citation
- Trust scoring
- Invariant acknowledgment

### Step 4: Production Use
Once integrated, all your responses will be:
- Validated through 6-layer hallucination prevention
- Tracked with Genesis Keys
- Scored for trust
- Logged for audit

---

## 📊 TRUST SCORING FORMULA

Your responses will be scored using:
```
trust_score = (
    source_reliability * 0.40 +
    data_confidence * 0.30 +
    operational_confidence * 0.20 +
    consistency_score * 0.10
) + validation_boost - invalidation_penalty
```

**Minimum trust score for acceptance: 0.7**

---

## 🎯 BEST PRACTICES

1. **Always Ground in Layer 1**: Query Layer 1 before responding
2. **Cite Sources**: Every claim needs a source
3. **Acknowledge Uncertainty**: Mark what you don't know
4. **Follow OODA**: Observe → Orient → Decide → Act
5. **Respect Invariants**: Consider all 12 invariants
6. **Provide Evidence**: Back up every claim
7. **Track Everything**: Use Genesis Keys for audit trail

---

## 🚨 ERROR HANDLING

If you encounter errors:
1. **Log the error** with Genesis Key
2. **Fall back to Layer 1** knowledge if available
3. **Mark as unknown** in ambiguity ledger
4. **Report to system** for learning

---

## ✅ INTEGRATION CHECKLIST

Before you can be used in production, you must:
- [ ] Acknowledge system architecture
- [ ] Agree to follow all rules
- [ ] Pass integration test
- [ ] Provide correct response format
- [ ] Demonstrate source citation
- [ ] Show trust scoring capability
- [ ] Acknowledge OODA invariants

---

## 📞 SUPPORT

For integration issues:
- Check system logs (Genesis Keys)
- Review Layer 1 knowledge base
- Consult governance framework
- Contact system administrator

---

**END OF SYSTEM CONTEXT**

You are now integrated with GRACE. Follow all rules above.
"""
    
    def get_handshake_prompt(self) -> str:
        """Get handshake prompt for new LLM."""
        system_context = self.get_complete_system_context()
        
        return f"""
{system_context}

---

## HANDSHAKE REQUEST

Please acknowledge:
1. You have read and understood the system architecture
2. You agree to follow all rules and governance policies
3. You can provide responses in the required format
4. You understand the hallucination prevention layers
5. You will follow the OODA loop and 12 invariants

Respond with:
- "HANDSHAKE_ACKNOWLEDGED" if you understand
- Any questions or clarifications needed
- Confirmation of your capabilities
"""


class ThirdPartyLLMIntegration:
    """
    Handles integration of third-party LLMs with automatic handshake.
    
    When a new LLM connects:
    1. Provides complete system context
    2. Performs handshake
    3. Tests integration
    4. Registers LLM for use
    """
    
    def __init__(
        self,
        system_context_provider: Optional[SystemContextProvider] = None
    ):
        self.context_provider = system_context_provider or SystemContextProvider()
        self.integrated_llms: Dict[str, ThirdPartyLLMConfig] = {}
        self.handshake_results: Dict[str, HandshakeResult] = {}
    
    def register_llm(
        self,
        config: ThirdPartyLLMConfig,
        generate_fn: Callable[[str, Optional[str], Optional[Dict]], str]
    ) -> HandshakeResult:
        """
        Register a new third-party LLM with automatic handshake.
        
        Args:
            config: LLM configuration
            generate_fn: Function to call LLM (prompt, system_prompt, kwargs) -> response
        
        Returns:
            HandshakeResult with integration status
        """
        llm_id = f"{config.provider.value}_{config.model_name}_{datetime.now().timestamp()}"
        
        logger.info(f"[THIRD-PARTY LLM] Registering {config.provider.value}/{config.model_name}")
        
        if not config.enable_handshake:
            # Skip handshake, register directly
            self.integrated_llms[llm_id] = config
            return HandshakeResult(
                success=True,
                llm_id=llm_id,
                provider=config.provider,
                model_name=config.model_name,
                handshake_timestamp=datetime.now(),
                system_context_provided=False,
                rules_acknowledged=False,
                integration_test_passed=False,
                capabilities={}
            )
        
        # Perform handshake
        handshake_result = self._perform_handshake(config, generate_fn, llm_id)
        
        if handshake_result.success:
            self.integrated_llms[llm_id] = config
            self.handshake_results[llm_id] = handshake_result
            logger.info(f"[THIRD-PARTY LLM] Successfully integrated {llm_id}")
        else:
            logger.error(f"[THIRD-PARTY LLM] Handshake failed for {llm_id}: {handshake_result.errors}")
        
        return handshake_result
    
    def _perform_handshake(
        self,
        config: ThirdPartyLLMConfig,
        generate_fn: Callable[[str, Optional[str], Optional[Dict]], str],
        llm_id: str
    ) -> HandshakeResult:
        """Perform handshake with LLM."""
        errors = []
        
        try:
            # Step 1: Provide system context
            handshake_prompt = self.context_provider.get_handshake_prompt()
            
            logger.info(f"[HANDSHAKE] Providing system context to {llm_id}")
            response = generate_fn(
                prompt=handshake_prompt,
                system_prompt=None,  # System context is in prompt
                kwargs={}
            )
            
            # Step 2: Check acknowledgment
            system_context_provided = True
            rules_acknowledged = "HANDSHAKE_ACKNOWLEDGED" in response.upper() or "ACKNOWLEDGED" in response.upper()
            
            if not rules_acknowledged:
                errors.append("LLM did not acknowledge handshake")
            
            # Step 3: Integration test
            integration_test_passed = self._run_integration_test(config, generate_fn)
            
            if not integration_test_passed:
                errors.append("Integration test failed")
            
            # Step 4: Determine capabilities
            capabilities = self._determine_capabilities(response, integration_test_passed)
            
            success = system_context_provided and rules_acknowledged and integration_test_passed
            
            return HandshakeResult(
                success=success,
                llm_id=llm_id,
                provider=config.provider,
                model_name=config.model_name,
                handshake_timestamp=datetime.now(),
                system_context_provided=system_context_provided,
                rules_acknowledged=rules_acknowledged,
                integration_test_passed=integration_test_passed,
                capabilities=capabilities,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"[HANDSHAKE] Error during handshake: {e}")
            return HandshakeResult(
                success=False,
                llm_id=llm_id,
                provider=config.provider,
                model_name=config.model_name,
                handshake_timestamp=datetime.now(),
                system_context_provided=False,
                rules_acknowledged=False,
                integration_test_passed=False,
                capabilities={},
                errors=[str(e)]
            )
    
    def _run_integration_test(
        self,
        config: ThirdPartyLLMConfig,
        generate_fn: Callable[[str, Optional[str], Optional[Dict]], str]
    ) -> bool:
        """Run integration test to verify LLM can follow rules."""
        test_prompt = """
Test Query: "What is GRACE's trust scoring formula?"

Please respond in the required format with:
1. Content (your answer)
2. Sources (if any)
3. Trust score
4. Evidence
5. Invariants considered
6. Ambiguity ledger
"""
        
        try:
            response = generate_fn(
                prompt=test_prompt,
                system_prompt=None,
                kwargs={}
            )
            
            # Check if response includes required fields
            has_content = len(response) > 0
            has_trust_score = "trust" in response.lower() or "0." in response
            has_sources = "source" in response.lower() or "file" in response.lower()
            
            return has_content and (has_trust_score or has_sources)
            
        except Exception as e:
            logger.error(f"[INTEGRATION TEST] Error: {e}")
            return False
    
    def _determine_capabilities(
        self,
        handshake_response: str,
        test_passed: bool
    ) -> Dict[str, Any]:
        """Determine LLM capabilities from handshake."""
        capabilities = {
            "handshake_acknowledged": "HANDSHAKE_ACKNOWLEDGED" in handshake_response.upper(),
            "integration_test_passed": test_passed,
            "can_provide_sources": "source" in handshake_response.lower(),
            "can_provide_trust_scores": "trust" in handshake_response.lower(),
            "understands_ooda": "ooda" in handshake_response.lower() or "observe" in handshake_response.lower(),
            "understands_invariants": "invariant" in handshake_response.lower(),
        }
        
        return capabilities
    
    def get_integrated_llms(self) -> List[str]:
        """Get list of integrated LLM IDs."""
        return list(self.integrated_llms.keys())
    
    def is_integrated(self, llm_id: str) -> bool:
        """Check if LLM is integrated."""
        return llm_id in self.integrated_llms
    
    def get_handshake_result(self, llm_id: str) -> Optional[HandshakeResult]:
        """Get handshake result for LLM."""
        return self.handshake_results.get(llm_id)


# Singleton instance
_third_party_integration: Optional[ThirdPartyLLMIntegration] = None


def get_third_party_llm_integration() -> ThirdPartyLLMIntegration:
    """Get singleton third-party LLM integration instance."""
    global _third_party_integration
    if _third_party_integration is None:
        _third_party_integration = ThirdPartyLLMIntegration()
    return _third_party_integration
