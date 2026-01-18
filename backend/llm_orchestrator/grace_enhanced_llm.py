"""
Grace-Enhanced LLM System

Connects LLMs to Grace's cognitive architecture:
1. Genesis Keys - Track ALL LLM outputs for provenance and fine-tuning
2. Memory Mesh - Enhanced context from learned experiences
3. Anti-Hallucination - Verification and grounding
4. Cognitive Framework - OODA loop reasoning
5. Clarity Framework - Structured problem solving
6. Trust Scores - Evidence-weighted decisions
7. TimeSense - Time-aware generation
8. KPIs - Performance monitoring
9. Fine-Tuning Pipeline - Learn from successful generations

Every LLM interaction is logged with Genesis Keys for:
- Full provenance tracking
- Fine-tuning data collection
- Trust score evolution
- Performance analysis
"""

import logging
import json
import hashlib
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class LLMGenerationRecord:
    """Record of LLM generation for Genesis tracking and fine-tuning."""
    # Required fields first
    record_id: str
    genesis_key_id: str
    timestamp: datetime
    
    # Input
    prompt: str
    enhanced_prompt: str
    context_sources: List[str]
    
    # Output
    raw_output: str
    cleaned_output: str
    output_type: str  # code, text, json, etc.
    
    # Quality metrics
    trust_score: float
    hallucination_score: float
    verification_passed: bool
    
    # Model info
    model_name: str
    temperature: float
    tokens_in: int
    tokens_out: int
    generation_time_ms: float
    
    # Optional fields with defaults last
    execution_success: Optional[bool] = None
    is_good_example: bool = False
    feedback: Optional[str] = None
    used_for_finetuning: bool = False


@dataclass
class EnhancedContext:
    """Context enhanced by Grace systems."""
    original_prompt: str
    system_prompt: str
    memory_context: str
    episodic_context: str
    procedural_hints: str
    trust_context: str
    
    @property
    def full_enhanced_prompt(self) -> str:
        """Build the full enhanced prompt."""
        parts = [self.system_prompt]
        
        if self.memory_context:
            parts.append(f"\n## Relevant Knowledge:\n{self.memory_context}")
        
        if self.episodic_context:
            parts.append(f"\n## Past Experiences:\n{self.episodic_context}")
        
        if self.procedural_hints:
            parts.append(f"\n## Known Patterns:\n{self.procedural_hints}")
        
        if self.trust_context:
            parts.append(f"\n## Trust Guidelines:\n{self.trust_context}")
        
        parts.append(f"\n## Task:\n{self.original_prompt}")
        
        return "\n".join(parts)


# =============================================================================
# GRACE ENHANCED LLM
# =============================================================================

class GraceEnhancedLLM:
    """
    Grace-Enhanced LLM wrapper.
    
    Every generation is:
    1. Enhanced with Memory Mesh context
    2. Tracked with Genesis Keys
    3. Verified for hallucinations
    4. Scored for trust
    5. Logged for fine-tuning
    """
    
    # Grace System Prompt - Embeds architecture into LLM
    GRACE_SYSTEM_PROMPT = '''You are a Grace-aligned AI assistant. You follow the Grace cognitive architecture:

## OODA Loop Structure
1. OBSERVE: Gather all relevant context before responding
2. ORIENT: Analyze using known patterns and past experiences
3. DECIDE: Choose the best approach based on evidence
4. ACT: Execute with precision and verify results

## Core Principles
- **Deterministic First**: Prefer deterministic solutions over probabilistic ones
- **Trust-Based**: Weight evidence by trust scores
- **Memory-Informed**: Use past experiences to guide decisions
- **Verifiable**: Provide reasoning that can be verified
- **Honest**: Acknowledge uncertainty, never hallucinate

## Code Generation Rules
- Write complete, working code - no placeholders
- Handle edge cases explicitly
- Follow existing patterns in the codebase
- Test your logic mentally before outputting

## Response Format
For code: Output ONLY the code, no explanations unless asked
For analysis: Be concise and evidence-based
For decisions: State the reasoning chain clearly
'''

    def __init__(
        self,
        session=None,
        model_name: str = "deepseek-coder-v2:16b",
        enable_genesis: bool = True,
        enable_memory: bool = True,
        enable_anti_hallucination: bool = True,
        enable_finetuning_log: bool = True,
        finetuning_log_path: str = None
    ):
        self.session = session
        self.model_name = model_name
        self.enable_genesis = enable_genesis
        self.enable_memory = enable_memory
        self.enable_anti_hallucination = enable_anti_hallucination
        self.enable_finetuning_log = enable_finetuning_log
        
        # Fine-tuning log path
        self.finetuning_log_path = Path(finetuning_log_path) if finetuning_log_path else \
            Path(__file__).parent.parent.parent / "data" / "finetuning_logs"
        self.finetuning_log_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize subsystems
        self._init_genesis()
        self._init_memory_mesh()
        self._init_anti_hallucination()
        self._init_ollama_client()
        self._init_trust_system()
        self._init_cognitive_enforcer()
        
        # Statistics
        self.stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "hallucinations_caught": 0,
            "avg_trust_score": 0.0,
            "finetuning_examples": 0
        }
        
        logger.info(f"[GRACE-LLM] Enhanced LLM initialized: {model_name}")
    
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    def _init_genesis(self):
        """Initialize Genesis Key tracking."""
        self.genesis_service = None
        if not self.enable_genesis:
            return
        
        try:
            from genesis.genesis_key_service import GenesisKeyService
            if self.session:
                self.genesis_service = GenesisKeyService(self.session)
                logger.info("[GRACE-LLM] Genesis Key tracking enabled")
        except ImportError:
            try:
                from backend.genesis.genesis_key_service import GenesisKeyService
                if self.session:
                    self.genesis_service = GenesisKeyService(self.session)
                    logger.info("[GRACE-LLM] Genesis Key tracking enabled")
            except Exception as e:
                logger.debug(f"[GRACE-LLM] Genesis not available: {e}")
        except Exception as e:
            logger.debug(f"[GRACE-LLM] Genesis not available: {e}")
    
    def _init_memory_mesh(self):
        """Initialize Memory Mesh for context enhancement."""
        self.memory_mesh = None
        self.learning_memory = None
        self.episodic_buffer = None
        
        if not self.enable_memory:
            return
        
        kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
        
        # Try to load Memory Mesh
        try:
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            if self.session:
                self.memory_mesh = MemoryMeshIntegration(self.session, kb_path)
                logger.info("[GRACE-LLM] Memory Mesh connected")
        except ImportError:
            try:
                from backend.cognitive.memory_mesh_integration import MemoryMeshIntegration
                if self.session:
                    self.memory_mesh = MemoryMeshIntegration(self.session, kb_path)
                    logger.info("[GRACE-LLM] Memory Mesh connected")
            except:
                pass
        except Exception as e:
            logger.debug(f"[GRACE-LLM] Memory Mesh not available: {e}")
        
        # Try to load Learning Memory
        try:
            from cognitive.learning_memory import LearningMemoryManager
            if self.session:
                self.learning_memory = LearningMemoryManager(self.session)
        except ImportError:
            try:
                from backend.cognitive.learning_memory import LearningMemoryManager
                if self.session:
                    self.learning_memory = LearningMemoryManager(self.session)
            except:
                pass
        except:
            pass
        
        # Try to load Episodic Buffer
        try:
            from cognitive.episodic_memory import EpisodicBuffer
            if self.session:
                self.episodic_buffer = EpisodicBuffer(self.session)
        except ImportError:
            try:
                from backend.cognitive.episodic_memory import EpisodicBuffer
                if self.session:
                    self.episodic_buffer = EpisodicBuffer(self.session)
            except:
                pass
        except:
            pass
    
    def _init_anti_hallucination(self):
        """Initialize anti-hallucination guard."""
        self.hallucination_guard = None
        
        if not self.enable_anti_hallucination:
            return
        
        try:
            from llm_orchestrator.hallucination_guard import HallucinationGuard
            self.hallucination_guard = HallucinationGuard()
            logger.info("[GRACE-LLM] Anti-hallucination guard enabled")
        except Exception as e:
            logger.warning(f"[GRACE-LLM] Hallucination guard not available: {e}")
    
    def _init_ollama_client(self):
        """Initialize Ollama client for local LLM."""
        self.ollama_url = "http://localhost:11434"
        
        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                logger.info(f"[GRACE-LLM] Ollama connected, models: {len(models)}")
        except Exception as e:
            logger.warning(f"[GRACE-LLM] Ollama not available: {e}")
    
    def _init_trust_system(self):
        """Initialize trust scoring system."""
        self.trust_scorer = None
        try:
            from confidence_scorer.confidence_scorer import ConfidenceScorer
            self.trust_scorer = ConfidenceScorer()
        except:
            pass
    
    def _init_cognitive_enforcer(self):
        """Initialize cognitive enforcer for OODA compliance."""
        self.cognitive_enforcer = None
        try:
            from llm_orchestrator.cognitive_enforcer import CognitiveEnforcer
            self.cognitive_enforcer = CognitiveEnforcer()
        except:
            pass
    
    # =========================================================================
    # CONTEXT ENHANCEMENT
    # =========================================================================
    
    def enhance_context(
        self,
        prompt: str,
        task_type: str = "code_generation",
        additional_context: Dict[str, Any] = None
    ) -> EnhancedContext:
        """
        Enhance prompt with Memory Mesh context.
        
        This expands the effective context window by retrieving
        relevant memories, past experiences, and known patterns.
        """
        memory_context = ""
        episodic_context = ""
        procedural_hints = ""
        trust_context = ""
        
        # 1. Query Memory Mesh for relevant knowledge
        if self.memory_mesh:
            try:
                # Search learning memory for similar problems
                if self.learning_memory:
                    similar = self.learning_memory.search_similar(
                        query=prompt[:500],
                        limit=5,
                        min_trust_score=0.6
                    )
                    if similar:
                        memory_parts = []
                        for mem in similar:
                            if hasattr(mem, 'learning_data'):
                                data = mem.learning_data if isinstance(mem.learning_data, dict) else {}
                                memory_parts.append(f"- {data.get('summary', str(mem)[:200])}")
                        memory_context = "\n".join(memory_parts)
            except Exception as e:
                logger.debug(f"Memory search failed: {e}")
        
        # 2. Query episodic memory for past experiences
        if self.episodic_buffer:
            try:
                episodes = self.episodic_buffer.recall_similar(
                    context=prompt[:300],
                    limit=3
                )
                if episodes:
                    episodic_parts = []
                    for ep in episodes:
                        outcome = "succeeded" if ep.get("success") else "failed"
                        episodic_parts.append(f"- Similar task {outcome}: {ep.get('summary', '')[:150]}")
                    episodic_context = "\n".join(episodic_parts)
            except:
                pass
        
        # 3. Get procedural hints from known patterns
        try:
            from backend.benchmarking.planning_workflow import get_planning_workflow
            planner = get_planning_workflow()
            plan_name, confidence = planner.classify_problem(prompt)
            if plan_name and confidence > 0.3:
                plan = planner.plans.get(plan_name, {})
                steps = plan.get("steps", [])
                if steps:
                    procedural_hints = f"Known pattern: {plan_name}\nSteps: {', '.join(steps)}"
        except:
            pass
        
        # 4. Add trust-based guidelines
        if task_type == "code_generation":
            trust_context = """Code must be:
- Complete and executable (no TODOs, no placeholders)
- Handle edge cases (empty inputs, None values)
- Follow the function signature exactly
- Return the correct type"""
        
        return EnhancedContext(
            original_prompt=prompt,
            system_prompt=self.GRACE_SYSTEM_PROMPT,
            memory_context=memory_context,
            episodic_context=episodic_context,
            procedural_hints=procedural_hints,
            trust_context=trust_context
        )
    
    # =========================================================================
    # GENERATION WITH GENESIS TRACKING
    # =========================================================================
    
    def generate(
        self,
        prompt: str,
        task_type: str = "code_generation",
        max_tokens: int = 500,
        temperature: float = 0.1,
        verify_output: bool = True,
        track_for_finetuning: bool = True
    ) -> Dict[str, Any]:
        """
        Generate with full Grace enhancement and Genesis tracking.
        
        Every generation is:
        1. Enhanced with memory context
        2. Tracked with Genesis Key
        3. Verified for quality
        4. Logged for fine-tuning
        """
        start_time = time.time()
        self.stats["total_generations"] += 1
        
        # 1. Create Genesis Key for this generation
        genesis_key_id = self._create_genesis_key(prompt, task_type)
        
        # 2. Enhance context with Memory Mesh
        enhanced = self.enhance_context(prompt, task_type)
        full_prompt = enhanced.full_enhanced_prompt
        
        # 3. Generate with Ollama
        raw_output = self._call_ollama(full_prompt, max_tokens, temperature)
        
        # 4. Clean and extract code
        cleaned_output = self._clean_output(raw_output, task_type)
        
        # 5. Calculate trust score
        trust_score = self._calculate_trust_score(
            prompt, cleaned_output, task_type
        )
        
        # 6. Check for hallucinations
        hallucination_score = 0.0
        verification_passed = True
        if verify_output and self.hallucination_guard:
            try:
                result = self.hallucination_guard.check_response(
                    prompt=prompt,
                    response=cleaned_output,
                    context={"task_type": task_type}
                )
                hallucination_score = result.get("hallucination_score", 0.0)
                verification_passed = hallucination_score < 0.3
                if not verification_passed:
                    self.stats["hallucinations_caught"] += 1
            except:
                pass
        
        generation_time = (time.time() - start_time) * 1000
        
        # 7. Create generation record
        record = LLMGenerationRecord(
            record_id=hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()[:16],
            genesis_key_id=genesis_key_id or "no_genesis",
            timestamp=datetime.now(),
            prompt=prompt,
            enhanced_prompt=full_prompt,
            context_sources=self._get_context_sources(enhanced),
            raw_output=raw_output,
            cleaned_output=cleaned_output,
            output_type=task_type,
            trust_score=trust_score,
            hallucination_score=hallucination_score,
            verification_passed=verification_passed,
            model_name=self.model_name,
            temperature=temperature,
            tokens_in=len(full_prompt.split()),
            tokens_out=len(raw_output.split()),
            generation_time_ms=generation_time,
            is_good_example=trust_score > 0.7 and verification_passed
        )
        
        # 8. Log for fine-tuning
        if track_for_finetuning and self.enable_finetuning_log:
            self._log_for_finetuning(record)
        
        # 9. Update Genesis Key with result
        self._update_genesis_key(genesis_key_id, record)
        
        # 10. Update stats
        if cleaned_output and len(cleaned_output) > 10:
            self.stats["successful_generations"] += 1
        
        # Update running average trust score
        n = self.stats["total_generations"]
        self.stats["avg_trust_score"] = (
            (self.stats["avg_trust_score"] * (n-1) + trust_score) / n
        )
        
        return {
            "content": cleaned_output,
            "raw_output": raw_output,
            "trust_score": trust_score,
            "hallucination_score": hallucination_score,
            "verification_passed": verification_passed,
            "genesis_key_id": genesis_key_id,
            "generation_time_ms": generation_time,
            "model": self.model_name,
            "enhanced": True,
            "context_sources": record.context_sources
        }
    
    def generate_code(
        self,
        problem: str,
        function_name: str,
        test_cases: List[str] = None
    ) -> str:
        """
        Generate code for a specific problem.
        
        Optimized for MBPP/HumanEval style problems.
        """
        # Build code-specific prompt
        prompt = f"""Write a Python function named `{function_name}` that:
{problem}

Requirements:
- Function must be named exactly: {function_name}
- Write ONLY the function definition, no examples or explanations
- Handle edge cases (empty input, None, etc.)
- The function must be complete and working
"""
        
        if test_cases:
            prompt += f"\nTest cases for reference:\n"
            for tc in test_cases[:3]:
                prompt += f"  {tc}\n"
        
        result = self.generate(
            prompt=prompt,
            task_type="code_generation",
            max_tokens=800,
            temperature=0.1,
            verify_output=True
        )
        
        return result.get("content", "")
    
    # =========================================================================
    # OLLAMA INTEGRATION
    # =========================================================================
    
    def _call_ollama(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1
    ) -> str:
        """Call Ollama API for generation."""
        try:
            import requests
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "top_p": 0.9,
                        "stop": ["```\n\n", "\n\ndef ", "\nclass "]
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return ""
    
    # =========================================================================
    # OUTPUT PROCESSING
    # =========================================================================
    
    def _clean_output(self, raw_output: str, task_type: str) -> str:
        """Clean and extract relevant output."""
        if not raw_output:
            return ""
        
        if task_type == "code_generation":
            return self._extract_code(raw_output)
        
        return raw_output.strip()
    
    def _extract_code(self, text: str) -> str:
        """Extract Python code from LLM output."""
        import re
        
        # Try to extract from code blocks
        code_block = re.search(r'```(?:python)?\s*\n(.*?)```', text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()
        
        # Find function definition
        func_match = re.search(
            r'(def\s+\w+\s*\([^)]*\)\s*:.*?)(?=\n\ndef\s|\n\nclass\s|\Z)',
            text,
            re.DOTALL
        )
        if func_match:
            return func_match.group(1).strip()
        
        # Return as-is if it looks like code
        if text.strip().startswith('def '):
            return text.strip()
        
        return ""
    
    # =========================================================================
    # GENESIS KEY TRACKING
    # =========================================================================
    
    def _create_genesis_key(self, prompt: str, task_type: str) -> Optional[str]:
        """Create Genesis Key for this generation."""
        if not self.genesis_service:
            return None
        
        try:
            from models.genesis_key_models import GenesisKeyType
            
            key = self.genesis_service.create_key(
                key_type=GenesisKeyType.LLM_GENERATION,
                what_description=f"LLM Generation: {task_type}",
                who_actor="GraceEnhancedLLM",
                where_location=f"model:{self.model_name}",
                why_reason=f"Generate {task_type} from prompt",
                how_method="grace_enhanced_llm.generate",
                context_data={
                    "prompt_preview": prompt[:200],
                    "task_type": task_type,
                    "model": self.model_name
                }
            )
            return key.key_id if hasattr(key, 'key_id') else str(key)
        except Exception as e:
            logger.debug(f"Genesis key creation failed: {e}")
            return None
    
    def _update_genesis_key(self, genesis_key_id: str, record: LLMGenerationRecord):
        """Update Genesis Key with generation result."""
        if not self.genesis_service or not genesis_key_id:
            return
        
        try:
            self.genesis_service.add_context(
                key_id=genesis_key_id,
                context={
                    "trust_score": record.trust_score,
                    "hallucination_score": record.hallucination_score,
                    "verification_passed": record.verification_passed,
                    "tokens_out": record.tokens_out,
                    "generation_time_ms": record.generation_time_ms,
                    "is_good_example": record.is_good_example
                }
            )
        except:
            pass
    
    # =========================================================================
    # TRUST SCORING
    # =========================================================================
    
    def _calculate_trust_score(
        self,
        prompt: str,
        output: str,
        task_type: str
    ) -> float:
        """Calculate trust score for generation."""
        if not output:
            return 0.0
        
        score = 0.5  # Base score
        
        # Code-specific checks
        if task_type == "code_generation":
            # Has function definition
            if "def " in output:
                score += 0.1
            
            # Has return statement
            if "return " in output:
                score += 0.1
            
            # No placeholders
            if "TODO" not in output and "pass" not in output.split("\n")[-1]:
                score += 0.1
            
            # Reasonable length
            if 20 < len(output) < 5000:
                score += 0.1
            
            # No obvious errors
            try:
                import ast
                ast.parse(output)
                score += 0.1  # Syntactically valid
            except:
                score -= 0.2
        
        return min(1.0, max(0.0, score))
    
    # =========================================================================
    # FINE-TUNING LOGGING
    # =========================================================================
    
    def _log_for_finetuning(self, record: LLMGenerationRecord):
        """Log generation for fine-tuning data collection."""
        if not record.is_good_example:
            return  # Only log good examples
        
        log_file = self.finetuning_log_path / f"finetuning_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        entry = {
            "timestamp": record.timestamp.isoformat(),
            "genesis_key_id": record.genesis_key_id,
            "prompt": record.prompt,
            "output": record.cleaned_output,
            "trust_score": record.trust_score,
            "model": record.model_name,
            "task_type": record.output_type
        }
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self.stats["finetuning_examples"] += 1
        except Exception as e:
            logger.warning(f"Failed to log for finetuning: {e}")
    
    def _get_context_sources(self, enhanced: EnhancedContext) -> List[str]:
        """Get list of context sources used."""
        sources = ["grace_system_prompt"]
        if enhanced.memory_context:
            sources.append("memory_mesh")
        if enhanced.episodic_context:
            sources.append("episodic_memory")
        if enhanced.procedural_hints:
            sources.append("procedural_patterns")
        return sources
    
    # =========================================================================
    # FEEDBACK AND LEARNING
    # =========================================================================
    
    def record_feedback(
        self,
        genesis_key_id: str,
        success: bool,
        feedback: str = None,
        execution_result: Dict[str, Any] = None
    ):
        """
        Record feedback on a generation for learning.
        
        This updates trust scores and marks examples for fine-tuning.
        """
        if self.memory_mesh:
            try:
                self.memory_mesh.ingest_learning_experience(
                    experience_type="success" if success else "failure",
                    context={"genesis_key_id": genesis_key_id},
                    action_taken={"type": "llm_generation"},
                    outcome={"success": success, "feedback": feedback},
                    source="user_feedback",
                    genesis_key_id=genesis_key_id
                )
            except:
                pass
        
        # Update Genesis Key
        if self.genesis_service and genesis_key_id:
            try:
                self.genesis_service.add_context(
                    key_id=genesis_key_id,
                    context={
                        "execution_success": success,
                        "feedback": feedback,
                        "execution_result": execution_result
                    }
                )
            except:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_generations"] / max(1, self.stats["total_generations"])
            ),
            "model": self.model_name,
            "finetuning_log_path": str(self.finetuning_log_path)
        }


# =============================================================================
# SINGLETON AND FACTORY
# =============================================================================

_grace_enhanced_llm: Optional[GraceEnhancedLLM] = None


def get_grace_enhanced_llm(
    session=None,
    model_name: str = "deepseek-coder-v2:16b",
    **kwargs
) -> GraceEnhancedLLM:
    """Get or create Grace-enhanced LLM instance."""
    global _grace_enhanced_llm
    
    if _grace_enhanced_llm is None:
        _grace_enhanced_llm = GraceEnhancedLLM(
            session=session,
            model_name=model_name,
            **kwargs
        )
    
    return _grace_enhanced_llm
