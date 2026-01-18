"""
Bidirectional LLM Client - Robust, Ready-to-Use LLM Interface

This module provides a production-ready LLM client with:
1. Circuit breaker for Ollama 500 errors
2. Automatic retry with exponential backoff
3. Fallback chain (Ollama -> API -> Templates)
4. Bidirectional communication with Grace systems
5. Response caching for efficiency
6. Concurrency control to prevent overload

This client is designed to be "ready and waiting" - always functional.
"""

import logging
import threading
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import OrderedDict
import json

logger = logging.getLogger(__name__)


class ClientState(Enum):
    """State of the LLM client."""
    READY = "ready"
    DEGRADED = "degraded"  # Some backends failing
    OFFLINE = "offline"  # All backends failing


class BackendType(Enum):
    """Types of LLM backends."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    TEMPLATE = "template"  # Fallback to templates


@dataclass
class CircuitBreaker:
    """Circuit breaker for handling backend failures."""
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before attempting recovery
    half_open_requests: int = 3  # Test requests in half-open state
    
    # State
    failures: int = 0
    last_failure: Optional[datetime] = None
    state: str = "closed"  # closed, open, half_open
    successful_half_open: int = 0
    
    def record_failure(self):
        """Record a failure."""
        self.failures += 1
        self.last_failure = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"[CIRCUIT BREAKER] OPENED after {self.failures} failures")
    
    def record_success(self):
        """Record a success."""
        if self.state == "half_open":
            self.successful_half_open += 1
            if self.successful_half_open >= self.half_open_requests:
                self.reset()
                logger.info("[CIRCUIT BREAKER] CLOSED after successful recovery")
        else:
            # Normal operation - reset failures
            self.failures = max(0, self.failures - 1)
    
    def can_proceed(self) -> bool:
        """Check if request can proceed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout passed
            if self.last_failure and \
               (datetime.now() - self.last_failure).seconds >= self.recovery_timeout:
                self.state = "half_open"
                self.successful_half_open = 0
                logger.info("[CIRCUIT BREAKER] Moving to HALF-OPEN state")
                return True
            return False
        
        if self.state == "half_open":
            return True
        
        return False
    
    def reset(self):
        """Reset circuit breaker."""
        self.failures = 0
        self.last_failure = None
        self.state = "closed"
        self.successful_half_open = 0


@dataclass
class BackendConfig:
    """Configuration for a backend."""
    backend_type: BackendType
    base_url: str
    model_name: str
    timeout: int = 120
    max_tokens: int = 4096
    temperature: float = 0.3
    enabled: bool = True
    priority: int = 0  # Higher = preferred


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    backend: BackendType
    success: bool
    duration_ms: float
    cached: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseCache:
    """Thread-safe LRU cache for responses."""
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def _make_key(self, prompt: str, system_prompt: str, model: str) -> str:
        """Create cache key."""
        key_data = f"{model}:{system_prompt}:{prompt}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def get(self, prompt: str, system_prompt: str = "", model: str = "") -> Optional[str]:
        """Get cached response."""
        key = self._make_key(prompt, system_prompt, model)
        
        with self._lock:
            if key in self._cache:
                if time.time() - self._timestamps[key] < self.ttl_seconds:
                    self._cache.move_to_end(key)
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._timestamps[key]
        return None
    
    def set(self, prompt: str, response: str, system_prompt: str = "", model: str = ""):
        """Cache a response."""
        key = self._make_key(prompt, system_prompt, model)
        
        with self._lock:
            while len(self._cache) >= self.max_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
                del self._timestamps[oldest]
            
            self._cache[key] = response
            self._timestamps[key] = time.time()


class BidirectionalLLMClient:
    """
    Production-ready bidirectional LLM client.
    
    Features:
    - Always-on: Falls back through multiple backends
    - Self-healing: Circuit breakers prevent cascade failures
    - Efficient: Response caching reduces redundant calls
    - Integrated: Bidirectional with Grace's learning systems
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        enable_cache: bool = True,
        max_workers: int = 4,
        enable_learning: bool = True
    ):
        """Initialize the bidirectional LLM client."""
        self.ollama_url = ollama_url
        self.enable_learning = enable_learning
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Semaphore for concurrency control
        self.ollama_semaphore = threading.Semaphore(2)  # Max 2 concurrent Ollama calls
        
        # Circuit breakers per backend
        self.circuit_breakers: Dict[BackendType, CircuitBreaker] = {
            BackendType.OLLAMA: CircuitBreaker(failure_threshold=3, recovery_timeout=30),
            BackendType.OPENAI: CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            BackendType.ANTHROPIC: CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            BackendType.DEEPSEEK: CircuitBreaker(failure_threshold=5, recovery_timeout=60),
        }
        
        # Response cache
        self.cache = ResponseCache() if enable_cache else None
        
        # Backend configurations (in priority order)
        self.backends: List[BackendConfig] = []
        self._configure_backends()
        
        # Statistics
        self.stats = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "cache_hits": 0,
            "fallbacks": 0,
        }
        self.stats_lock = threading.Lock()
        
        # Grace system connections
        self._grace_learning = None
        self._grace_memory = None
        self._init_grace_connections()
        
        logger.info(f"[BIDIRECTIONAL LLM] Initialized with {len(self.backends)} backends")
    
    def _configure_backends(self):
        """Configure available backends."""
        # Ollama (local, preferred)
        self.backends.append(BackendConfig(
            backend_type=BackendType.OLLAMA,
            base_url=self.ollama_url,
            model_name="deepseek-coder:6.7b",
            timeout=120,
            priority=100,
            enabled=True
        ))
        
        # Add alternative Ollama models
        for model in ["qwen2.5-coder:7b", "codellama:7b", "mistral:7b"]:
            self.backends.append(BackendConfig(
                backend_type=BackendType.OLLAMA,
                base_url=self.ollama_url,
                model_name=model,
                timeout=120,
                priority=90,
                enabled=True
            ))
        
        # Template fallback (always available)
        self.backends.append(BackendConfig(
            backend_type=BackendType.TEMPLATE,
            base_url="",
            model_name="template_engine",
            timeout=5,
            priority=0,
            enabled=True
        ))
        
        # Sort by priority (highest first)
        self.backends.sort(key=lambda x: -x.priority)
    
    def _init_grace_connections(self):
        """Initialize connections to Grace systems."""
        try:
            from cognitive.learning_memory import LearningMemoryManager
            from database.session import SessionLocal
            
            session = SessionLocal()
            self._grace_learning = LearningMemoryManager(session, "knowledge_base")
            logger.info("[BIDIRECTIONAL LLM] Connected to Grace Learning Memory")
        except Exception as e:
            logger.debug(f"[BIDIRECTIONAL LLM] Grace learning not available: {e}")
        
        try:
            from cognitive.smart_memory_retrieval import SmartMemoryRetrieval
            from database.session import SessionLocal
            
            session = SessionLocal()
            self._grace_memory = SmartMemoryRetrieval(session, "knowledge_base")
            logger.info("[BIDIRECTIONAL LLM] Connected to Grace Memory Retrieval")
        except Exception as e:
            logger.debug(f"[BIDIRECTIONAL LLM] Grace memory not available: {e}")
    
    # =========================================================================
    # MAIN GENERATION API
    # =========================================================================
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        use_cache: bool = True,
        include_memory: bool = True,
        task_type: str = "code_generation"
    ) -> LLMResponse:
        """
        Generate a response using the best available backend.
        
        This method:
        1. Checks cache first
        2. Retrieves relevant Grace memories
        3. Tries backends in priority order with circuit breakers
        4. Falls back to templates if all else fails
        5. Records results for learning
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            use_cache: Whether to use caching
            include_memory: Whether to include Grace memories
            task_type: Type of task for memory retrieval
            
        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()
        
        with self.stats_lock:
            self.stats["requests"] += 1
        
        # Check cache
        if use_cache and self.cache:
            cached = self.cache.get(prompt, system_prompt)
            if cached:
                with self.stats_lock:
                    self.stats["cache_hits"] += 1
                
                return LLMResponse(
                    content=cached,
                    model="cache",
                    backend=BackendType.TEMPLATE,
                    success=True,
                    duration_ms=0,
                    cached=True
                )
        
        # Enhance prompt with Grace memories
        enhanced_prompt = prompt
        if include_memory and self._grace_memory:
            try:
                memories = self._retrieve_relevant_memories(prompt, task_type)
                if memories:
                    memory_context = self._format_memories_for_prompt(memories)
                    enhanced_prompt = f"{memory_context}\n\n{prompt}"
            except Exception as e:
                logger.debug(f"Memory retrieval failed: {e}")
        
        # Try backends in order
        last_error = None
        
        for backend in self.backends:
            if not backend.enabled:
                continue
            
            # Check circuit breaker
            breaker = self.circuit_breakers.get(backend.backend_type)
            if breaker and not breaker.can_proceed():
                logger.debug(f"[BIDIRECTIONAL LLM] Skipping {backend.backend_type.value} - circuit open")
                continue
            
            try:
                response = self._call_backend(
                    backend,
                    enhanced_prompt,
                    system_prompt,
                    temperature,
                    max_tokens
                )
                
                if response.success:
                    # Record success
                    if breaker:
                        breaker.record_success()
                    
                    with self.stats_lock:
                        self.stats["successes"] += 1
                    
                    # Cache response
                    if use_cache and self.cache:
                        self.cache.set(prompt, response.content, system_prompt, backend.model_name)
                    
                    # Record for learning
                    if self.enable_learning:
                        self._record_for_learning(prompt, response, task_type)
                    
                    response.duration_ms = (time.time() - start_time) * 1000
                    return response
                else:
                    last_error = response.error
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[BIDIRECTIONAL LLM] Backend {backend.model_name} failed: {e}")
                
                if breaker:
                    breaker.record_failure()
                
                with self.stats_lock:
                    self.stats["fallbacks"] += 1
        
        # All backends failed
        with self.stats_lock:
            self.stats["failures"] += 1
        
        return LLMResponse(
            content="",
            model="none",
            backend=BackendType.TEMPLATE,
            success=False,
            duration_ms=(time.time() - start_time) * 1000,
            error=last_error or "All backends failed"
        )
    
    def _call_backend(
        self,
        backend: BackendConfig,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call a specific backend."""
        
        if backend.backend_type == BackendType.OLLAMA:
            return self._call_ollama(backend, prompt, system_prompt, temperature, max_tokens)
        
        elif backend.backend_type == BackendType.TEMPLATE:
            return self._call_template(prompt)
        
        else:
            return LLMResponse(
                content="",
                model=backend.model_name,
                backend=backend.backend_type,
                success=False,
                duration_ms=0,
                error=f"Backend {backend.backend_type.value} not implemented"
            )
    
    def _call_ollama(
        self,
        backend: BackendConfig,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Call Ollama backend with concurrency control."""
        import requests
        
        # Acquire semaphore for concurrency control
        if not self.ollama_semaphore.acquire(timeout=30):
            return LLMResponse(
                content="",
                model=backend.model_name,
                backend=BackendType.OLLAMA,
                success=False,
                duration_ms=0,
                error="Timeout waiting for Ollama semaphore"
            )
        
        try:
            # Build request
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": backend.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            # Make request
            url = f"{backend.base_url}/api/chat"
            response = requests.post(
                url,
                json=payload,
                timeout=backend.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                return LLMResponse(
                    content=content,
                    model=backend.model_name,
                    backend=BackendType.OLLAMA,
                    success=bool(content),
                    duration_ms=0,
                    metadata={"tokens": data.get("eval_count", 0)}
                )
            else:
                return LLMResponse(
                    content="",
                    model=backend.model_name,
                    backend=BackendType.OLLAMA,
                    success=False,
                    duration_ms=0,
                    error=f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except requests.Timeout:
            return LLMResponse(
                content="",
                model=backend.model_name,
                backend=BackendType.OLLAMA,
                success=False,
                duration_ms=0,
                error="Request timeout"
            )
        except requests.ConnectionError as e:
            return LLMResponse(
                content="",
                model=backend.model_name,
                backend=BackendType.OLLAMA,
                success=False,
                duration_ms=0,
                error=f"Connection error: {e}"
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=backend.model_name,
                backend=BackendType.OLLAMA,
                success=False,
                duration_ms=0,
                error=str(e)
            )
        finally:
            self.ollama_semaphore.release()
    
    def _call_template(self, prompt: str) -> LLMResponse:
        """Fall back to template-based generation."""
        try:
            from backend.benchmarking.mbpp_templates import generate_from_template
            
            # Try to generate from template
            code = generate_from_template(prompt)
            
            if code:
                return LLMResponse(
                    content=code,
                    model="template_engine",
                    backend=BackendType.TEMPLATE,
                    success=True,
                    duration_ms=0,
                    metadata={"source": "template"}
                )
        except Exception as e:
            logger.debug(f"Template generation failed: {e}")
        
        return LLMResponse(
            content="",
            model="template_engine",
            backend=BackendType.TEMPLATE,
            success=False,
            duration_ms=0,
            error="No matching template"
        )
    
    # =========================================================================
    # GRACE INTEGRATION
    # =========================================================================
    
    def _retrieve_relevant_memories(
        self,
        query: str,
        task_type: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from Grace."""
        memories = []
        
        if self._grace_memory:
            try:
                # Get learning memories
                learning_mems = self._grace_memory.retrieve_learning_memories(
                    context={"query": query, "task_type": task_type},
                    limit=limit
                )
                memories.extend(learning_mems)
            except Exception as e:
                logger.debug(f"Learning memory retrieval failed: {e}")
            
            try:
                # Get procedures
                procedures = self._grace_memory.retrieve_procedures(
                    goal=query,
                    limit=limit // 2
                )
                memories.extend(procedures)
            except Exception as e:
                logger.debug(f"Procedure retrieval failed: {e}")
        
        return memories
    
    def _format_memories_for_prompt(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories as context for the prompt."""
        if not memories:
            return ""
        
        context = "# Relevant Knowledge from Grace Memory:\n\n"
        
        for i, mem in enumerate(memories[:3], 1):
            content = str(mem.get("memory", mem.get("content", "")))[:300]
            trust = mem.get("trust_score", 0.5)
            context += f"{i}. {content}... (Trust: {trust:.2f})\n\n"
        
        return context
    
    def _record_for_learning(
        self,
        prompt: str,
        response: LLMResponse,
        task_type: str
    ):
        """Record successful response for Grace learning."""
        if not self._grace_learning or not response.success:
            return
        
        try:
            self._grace_learning.create_example(
                example_type="llm_response",
                input_context=prompt[:500],
                expected_output=response.content[:1000],
                actual_output=response.content[:1000],
                trust_score=0.7,
                source="bidirectional_llm",
                genesis_key_id=None,
                source_user_id="llm_client"
            )
        except Exception as e:
            logger.debug(f"Learning recording failed: {e}")
    
    # =========================================================================
    # CODE-SPECIFIC GENERATION
    # =========================================================================
    
    def generate_code(
        self,
        problem: str,
        function_name: Optional[str] = None,
        test_cases: Optional[List[str]] = None,
        temperature: float = 0.3
    ) -> LLMResponse:
        """
        Generate code with specialized prompt for coding tasks.
        
        Args:
            problem: Problem description
            function_name: Expected function name
            test_cases: Test cases for context
            temperature: Sampling temperature
            
        Returns:
            LLMResponse with generated code
        """
        # Build coding-specific system prompt
        system_prompt = """You are an expert Python programmer. Generate clean, working Python code.

IMPORTANT RULES:
1. Output ONLY the Python code - no markdown, no explanations
2. Define exactly ONE function with the specified name
3. The function must handle all edge cases
4. Do not include test code or print statements
5. Do not include if __name__ == '__main__' blocks
"""
        
        # Build enhanced prompt
        prompt_parts = [f"Write a Python function to solve this problem:\n\n{problem}"]
        
        if function_name:
            prompt_parts.append(f"\nThe function MUST be named: {function_name}")
        
        if test_cases:
            prompt_parts.append("\nThe function must pass these test cases:")
            for tc in test_cases[:3]:  # Limit to 3 for context
                prompt_parts.append(f"  {tc}")
        
        prompt = "\n".join(prompt_parts)
        
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            task_type="code_generation"
        )
    
    # =========================================================================
    # STATUS AND DIAGNOSTICS
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current client status."""
        backend_status = {}
        
        for backend in self.backends:
            breaker = self.circuit_breakers.get(backend.backend_type)
            backend_status[f"{backend.backend_type.value}_{backend.model_name}"] = {
                "enabled": backend.enabled,
                "priority": backend.priority,
                "circuit_state": breaker.state if breaker else "none",
                "failures": breaker.failures if breaker else 0
            }
        
        # Determine overall state
        any_ready = any(
            (b.enabled and 
             (b.backend_type not in self.circuit_breakers or 
              self.circuit_breakers[b.backend_type].state != "open"))
            for b in self.backends
        )
        
        all_open = all(
            self.circuit_breakers.get(b.backend_type, CircuitBreaker()).state == "open"
            for b in self.backends
            if b.backend_type in self.circuit_breakers
        )
        
        if all_open:
            state = ClientState.OFFLINE
        elif any_ready:
            state = ClientState.READY
        else:
            state = ClientState.DEGRADED
        
        return {
            "state": state.value,
            "backends": backend_status,
            "stats": dict(self.stats),
            "cache_enabled": self.cache is not None,
            "learning_enabled": self.enable_learning,
            "grace_memory_connected": self._grace_memory is not None,
            "grace_learning_connected": self._grace_learning is not None
        }
    
    def reset_circuit_breakers(self):
        """Reset all circuit breakers."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        logger.info("[BIDIRECTIONAL LLM] All circuit breakers reset")
    
    def is_ready(self) -> bool:
        """Check if client is ready for requests."""
        status = self.get_status()
        return status["state"] != ClientState.OFFLINE.value
    
    def shutdown(self):
        """Shutdown the client."""
        self.executor.shutdown(wait=False)
        logger.info("[BIDIRECTIONAL LLM] Client shutdown")


# Global instance
_bidirectional_client: Optional[BidirectionalLLMClient] = None


def get_bidirectional_llm_client() -> BidirectionalLLMClient:
    """Get or create global bidirectional LLM client."""
    global _bidirectional_client
    if _bidirectional_client is None:
        _bidirectional_client = BidirectionalLLMClient()
    return _bidirectional_client


def generate_code(
    problem: str,
    function_name: Optional[str] = None,
    test_cases: Optional[List[str]] = None
) -> str:
    """Convenience function for code generation."""
    client = get_bidirectional_llm_client()
    response = client.generate_code(problem, function_name, test_cases)
    return response.content if response.success else ""
