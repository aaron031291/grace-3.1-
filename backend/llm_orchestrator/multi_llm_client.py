"""
Multi-LLM Client - Manages multiple open-source LLMs via Ollama

Supports:
- DeepSeek Coder (code generation, debugging)
- Qwen 2.5 Coder (code understanding)
- DeepSeek-R1 (reasoning)
- Mistral Small (fast queries)
- Llama 3.x (general purpose)
- Gemma 2 (validation tasks)

Features:
- Model selection based on task type
- Load balancing
- Failover with automatic retry
- Performance tracking
- Rate limiting
- Response caching
- Production-ready error handling

Classes:
- `RateLimiter`
- `LRUCache`
- `RetryConfig`
- `TaskType`
- `ModelCapability`
- `LLMModel`
- `MultiLLMClient`

Key Methods:
- `acquire()`
- `get_status()`
- `get()`
- `set()`
- `clear()`
- `get_stats()`
- `get_delay()`
- `should_retry()`
- `select_model()`
- `generate()`
- `generate_multiple()`
- `get_available_models()`
- `get_model_stats()`
- `reset_stats()`
- `get_system_status()`
- `clear_cache()`
- `shutdown()`
- `get_multi_llm_client()`

Connects To:
Self-contained
"""

import logging
import hashlib
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import requests

from .base_client import BaseLLMClient
from .factory import get_llm_client
from settings import settings

logger = logging.getLogger(__name__)
def _check_hia(text):
    try:
        from security.honesty_integrity_accountability import get_hia_framework
        return get_hia_framework().verify_llm_output(text)
    except Exception:
        return None



# =============================================================================
# PRODUCTION HARDENING: Rate Limiter
# =============================================================================

class RateLimiter:
    """Token bucket rate limiter for LLM API calls."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        self._minute_tokens = requests_per_minute
        self._hour_tokens = requests_per_hour
        self._last_minute_refill = time.time()
        self._last_hour_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire a rate limit token. Blocks until available or timeout.

        Returns:
            True if acquired, False if timeout
        """
        start_time = time.time()

        while True:
            with self._lock:
                self._refill_tokens()

                if self._minute_tokens > 0 and self._hour_tokens > 0:
                    self._minute_tokens -= 1
                    self._hour_tokens -= 1
                    return True

            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning("[RATE LIMIT] Timeout waiting for rate limit token")
                return False

            # Wait before retry
            time.sleep(0.1)

    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()

        # Refill minute tokens
        minute_elapsed = now - self._last_minute_refill
        if minute_elapsed >= 60:
            self._minute_tokens = self.requests_per_minute
            self._last_minute_refill = now
        elif minute_elapsed >= 1:
            # Gradual refill
            refill = int(minute_elapsed * (self.requests_per_minute / 60))
            self._minute_tokens = min(self._minute_tokens + refill, self.requests_per_minute)
            self._last_minute_refill = now

        # Refill hour tokens
        hour_elapsed = now - self._last_hour_refill
        if hour_elapsed >= 3600:
            self._hour_tokens = self.requests_per_hour
            self._last_hour_refill = now

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        with self._lock:
            self._refill_tokens()
            return {
                "minute_tokens_remaining": self._minute_tokens,
                "hour_tokens_remaining": self._hour_tokens,
                "requests_per_minute": self.requests_per_minute,
                "requests_per_hour": self.requests_per_hour
            }


# =============================================================================
# PRODUCTION HARDENING: Response Cache
# =============================================================================

class LRUCache:
    """Thread-safe LRU cache for LLM responses."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, prompt: str, model_id: str, system_prompt: Optional[str]) -> str:
        """Create cache key from request parameters."""
        key_data = f"{model_id}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, prompt: str, model_id: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        key = self._make_key(prompt, model_id, system_prompt)

        with self._lock:
            if key in self._cache:
                # Check TTL
                if time.time() - self._timestamps[key] < self.ttl_seconds:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    logger.debug(f"[CACHE] Hit for key {key[:16]}...")
                    return self._cache[key].copy()
                else:
                    # Expired - remove
                    del self._cache[key]
                    del self._timestamps[key]

            self._misses += 1
            return None

    def set(self, prompt: str, model_id: str, response: Dict[str, Any], system_prompt: Optional[str] = None):
        """Cache a response."""
        key = self._make_key(prompt, model_id, system_prompt)

        with self._lock:
            # Remove oldest if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]

            self._cache[key] = response.copy()
            self._timestamps[key] = time.time()
            self._cache.move_to_end(key)

    def clear(self):
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "ttl_seconds": self.ttl_seconds
            }


# =============================================================================
# PRODUCTION HARDENING: Retry Logic
# =============================================================================

class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retry_on_errors: Optional[List[type]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_errors = retry_on_errors or [
            ConnectionError,
            TimeoutError,
            requests.exceptions.RequestException
        ]

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt number (0-indexed)."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    def should_retry(self, error: Exception) -> bool:
        """Check if error is retryable."""
        return any(isinstance(error, err_type) for err_type in self.retry_on_errors)


class TaskType(Enum):
    """Types of tasks for model selection."""
    CODE_GENERATION = "code_generation"
    CODE_DEBUGGING = "code_debugging"
    CODE_EXPLANATION = "code_explanation"
    CODE_REVIEW = "code_review"
    REASONING = "reasoning"
    PLANNING = "planning"
    VALIDATION = "validation"
    QUICK_QUERY = "quick_query"
    GENERAL = "general"


class ModelCapability(Enum):
    """Model capabilities."""
    CODE = "code"
    REASONING = "reasoning"
    SPEED = "speed"
    GENERAL = "general"


@dataclass
class LLMModel:
    """Configuration for an LLM model."""
    name: str
    model_id: str  # Ollama model ID
    capabilities: List[ModelCapability]
    context_window: int
    recommended_tasks: List[TaskType]
    priority: int  # Higher = preferred
    max_tokens: int = 2048
    temperature: float = 0.7


class MultiLLMClient:
    """
    Manages multiple LLM models for different tasks.

    Routes requests to appropriate models based on task type.
    """

    # Model registry with recommended configurations
    MODEL_REGISTRY = {
        "deepseek-coder-33b": LLMModel(
            name="DeepSeek Coder 33B",
            model_id="deepseek-coder:33b-instruct",
            capabilities=[ModelCapability.CODE, ModelCapability.REASONING],
            context_window=16384,
            recommended_tasks=[
                TaskType.CODE_GENERATION,
                TaskType.CODE_DEBUGGING,
                TaskType.CODE_EXPLANATION,
                TaskType.CODE_REVIEW
            ],
            priority=10
        ),
        "deepseek-coder-6.7b": LLMModel(
            name="DeepSeek Coder 6.7B",
            model_id="deepseek-coder:6.7b-instruct",
            capabilities=[ModelCapability.CODE],
            context_window=16384,
            recommended_tasks=[
                TaskType.CODE_GENERATION,
                TaskType.CODE_DEBUGGING
            ],
            priority=8
        ),
        "qwen2.5-coder-32b": LLMModel(
            name="Qwen 2.5 Coder 32B",
            model_id="qwen2.5-coder:32b-instruct",
            capabilities=[ModelCapability.CODE, ModelCapability.REASONING],
            context_window=32768,
            recommended_tasks=[
                TaskType.CODE_GENERATION,
                TaskType.CODE_EXPLANATION,
                TaskType.CODE_REVIEW
            ],
            priority=9
        ),
        "qwen2.5-coder-7b": LLMModel(
            name="Qwen 2.5 Coder 7B",
            model_id="qwen2.5-coder:7b-instruct",
            capabilities=[ModelCapability.CODE],
            context_window=32768,
            recommended_tasks=[
                TaskType.CODE_GENERATION,
                TaskType.QUICK_QUERY
            ],
            priority=7
        ),
        "deepseek-r1-70b": LLMModel(
            name="DeepSeek-R1 70B",
            model_id="deepseek-r1:70b",
            capabilities=[ModelCapability.REASONING],
            context_window=16384,
            recommended_tasks=[
                TaskType.REASONING,
                TaskType.PLANNING
            ],
            priority=10
        ),
        "deepseek-r1-7b": LLMModel(
            name="DeepSeek-R1 7B",
            model_id="deepseek-r1:7b",
            capabilities=[ModelCapability.REASONING],
            context_window=16384,
            recommended_tasks=[
                TaskType.REASONING,
                TaskType.VALIDATION
            ],
            priority=7
        ),
        "qwen2.5-72b": LLMModel(
            name="Qwen 2.5 72B",
            model_id="qwen2.5:72b-instruct",
            capabilities=[ModelCapability.REASONING, ModelCapability.GENERAL],
            context_window=32768,
            recommended_tasks=[
                TaskType.REASONING,
                TaskType.PLANNING,
                TaskType.GENERAL
            ],
            priority=9
        ),
        "mistral-small": LLMModel(
            name="Mistral Small",
            model_id="mistral-small:22b",
            capabilities=[ModelCapability.SPEED, ModelCapability.GENERAL],
            context_window=32768,
            recommended_tasks=[
                TaskType.QUICK_QUERY,
                TaskType.VALIDATION
            ],
            priority=8
        ),
        "llama3.3-70b": LLMModel(
            name="Llama 3.3 70B",
            model_id="llama3.3:70b-instruct",
            capabilities=[ModelCapability.GENERAL, ModelCapability.REASONING],
            context_window=8192,
            recommended_tasks=[
                TaskType.GENERAL,
                TaskType.REASONING
            ],
            priority=8
        ),
        "gemma2-27b": LLMModel(
            name="Gemma 2 27B",
            model_id="gemma2:27b-instruct",
            capabilities=[ModelCapability.GENERAL],
            context_window=8192,
            recommended_tasks=[
                TaskType.VALIDATION,
                TaskType.GENERAL
            ],
            priority=7
        ),
        "mistral-7b": LLMModel(
            name="Mistral 7B",
            model_id="mistral:7b",
            capabilities=[ModelCapability.GENERAL],
            context_window=8192,
            recommended_tasks=[
                TaskType.QUICK_QUERY,
                TaskType.GENERAL
            ],
            priority=6
        ),
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        enable_cache: bool = True,
        enable_rate_limiting: bool = True,
        cache_ttl_seconds: int = 3600,
        cache_max_size: int = 1000,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        max_retries: int = 3,
        max_concurrent_requests: int = 10
    ):
        """
        Initialize Multi-LLM client with production hardening.

        Args:
            base_url: Ollama base URL
            enable_cache: Enable response caching
            enable_rate_limiting: Enable rate limiting
            cache_ttl_seconds: Cache TTL in seconds
            cache_max_size: Maximum cache entries
            requests_per_minute: Rate limit per minute
            requests_per_hour: Rate limit per hour
            max_retries: Maximum retry attempts
            max_concurrent_requests: Maximum concurrent requests for parallel ops
        """
        self.llm_client = get_llm_client()
        self.available_models: Dict[str, LLMModel] = {}
        self.model_stats: Dict[str, Dict[str, Any]] = {}

        # Production hardening components
        self.cache = LRUCache(max_size=cache_max_size, ttl_seconds=cache_ttl_seconds) if enable_cache else None
        self.rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour
        ) if enable_rate_limiting else None
        self.retry_config = RetryConfig(max_retries=max_retries)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_requests)

        # Discover available models
        self._discover_models()

    def _discover_models(self):
        """Discover which models are installed and available."""
        try:
            # Get provider from settings
            provider = settings.LLM_PROVIDER
            
            if provider == "openai":
                # For OpenAI, we don't need to "discover" in the same way
                # We register the configured model for all tasks
                model_id = settings.LLM_MODEL or "gpt-4o"
                config = LLMModel(
                    name=f"OpenAI {model_id}",
                    model_id=model_id,
                    capabilities=[ModelCapability.GENERAL, ModelCapability.CODE, ModelCapability.REASONING],
                    context_window=128000,
                    recommended_tasks=list(TaskType),
                    priority=10
                )
                self.available_models[model_id] = config
                self.model_stats[model_id] = {
                    "requests": 0, "successes": 0, "failures": 0,
                    "total_duration_ms": 0, "avg_duration_ms": 0
                }
                logger.info(f"OpenAI Model configured: {model_id}")
                return

            installed_models = self.llm_client.get_all_models()
            # installed_models returns dicts from adapter/factory
            installed_model_names = {model['name'] for model in installed_models}

            for model_key, model_config in self.MODEL_REGISTRY.items():
                # Check if model is installed (handle version tags)
                model_base_name = model_config.model_id.split(':')[0]
                is_installed = any(
                    installed.startswith(model_base_name)
                    for installed in installed_model_names
                )

                if is_installed:
                    self.available_models[model_key] = model_config
                    self.model_stats[model_key] = {
                        "requests": 0,
                        "successes": 0,
                        "failures": 0,
                        "total_duration_ms": 0,
                        "avg_duration_ms": 0
                    }
                    logger.info(f"Model available: {model_config.name}")
                else:
                    logger.debug(f"Model not installed: {model_config.name}")

            if not self.available_models:
                logger.warning("No registered models found. Using default fallback.")
                # Add default fallback
                self.available_models["fallback"] = LLMModel(
                    name="Fallback Model",
                    model_id=settings.OLLAMA_LLM_DEFAULT,
                    capabilities=[ModelCapability.GENERAL],
                    context_window=4096,
                    recommended_tasks=[TaskType.GENERAL],
                    priority=1
                )

        except Exception as e:
            logger.error(f"Error discovering models: {e}")
            # Initialize with default fallback
            self.available_models["fallback"] = LLMModel(
                name="Fallback Model",
                model_id=settings.OLLAMA_LLM_DEFAULT,
                capabilities=[ModelCapability.GENERAL],
                context_window=4096,
                recommended_tasks=[TaskType.GENERAL],
                priority=1
            )

    def select_model(
        self,
        task_type: TaskType,
        required_capabilities: Optional[List[ModelCapability]] = None,
        prefer_speed: bool = False
    ) -> Optional[LLMModel]:
        """
        Select best model for task.

        Args:
            task_type: Type of task
            required_capabilities: Required model capabilities
            prefer_speed: Prefer faster models

        Returns:
            Best matching model or None
        """
        if not self.available_models:
            logger.error("No models available")
            return None

        # Filter models by task type
        candidates = [
            model for model in self.available_models.values()
            if task_type in model.recommended_tasks
        ]

        # If no matches, use models with required capabilities
        if not candidates and required_capabilities:
            candidates = [
                model for model in self.available_models.values()
                if any(cap in model.capabilities for cap in required_capabilities)
            ]

        # If still no matches, use any available model
        if not candidates:
            candidates = list(self.available_models.values())

        # Filter by required capabilities
        if required_capabilities:
            candidates = [
                model for model in candidates
                if all(cap in model.capabilities for cap in required_capabilities)
            ]

        if not candidates:
            logger.warning(f"No suitable model for task: {task_type}")
            return list(self.available_models.values())[0]  # Fallback to first available

        # Sort by priority (higher is better)
        candidates.sort(key=lambda m: (
            -m.priority if not prefer_speed else m.priority,
            -m.context_window
        ))

        selected = candidates[0]
        logger.info(f"Selected model: {selected.name} for task: {task_type.value}")
        return selected

    def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        use_cache: bool = True,
        skip_rate_limit: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response from selected model with production hardening.

        Features:
        - Response caching (for identical requests)
        - Rate limiting (prevents resource exhaustion)
        - Automatic retry with exponential backoff
        - Fallback to alternative models on failure

        Args:
            prompt: User prompt
            task_type: Type of task
            model_id: Specific model ID (optional, auto-selects if not provided)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt
            stream: Whether to stream response
            use_cache: Whether to use response caching
            skip_rate_limit: Skip rate limiting (use with caution)

        Returns:
            Response dictionary with content and metadata
        """
        start_time = datetime.now()

        try:
            # Select model
            if model_id:
                model = next(
                    (m for m in self.available_models.values() if m.model_id == model_id),
                    None
                )
                if not model:
                    model = self.select_model(task_type)
            else:
                model = self.select_model(task_type)

            if not model:
                raise ValueError("No suitable model available")

            # Check cache first (if enabled and not streaming)
            if use_cache and self.cache and not stream:
                cached = self.cache.get(prompt, model.model_id, system_prompt)
                if cached:
                    cached["from_cache"] = True
                    cached["duration_ms"] = 0
                    logger.info(f"[CACHE] Returning cached response for model {model.name}")
                    return cached

            # Rate limiting
            if not skip_rate_limit and self.rate_limiter:
                if not self.rate_limiter.acquire(timeout=30.0):
                    raise RuntimeError("Rate limit exceeded - request timeout")

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Update stats
            model_key = next(
                (k for k, v in self.available_models.items() if v.model_id == model.model_id),
                "unknown"
            )
            if model_key in self.model_stats:
                self.model_stats[model_key]["requests"] += 1

            # Generate with retry logic
            response_text = self._generate_with_retry(
                model=model,
                messages=messages,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                task_type=task_type
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Update success stats
            if model_key in self.model_stats:
                stats = self.model_stats[model_key]
                stats["successes"] += 1
                stats["total_duration_ms"] += duration_ms
                stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["successes"]

            result = {
                "content": response_text,
                "model_name": model.name,
                "model_id": model.model_id,
                "task_type": task_type.value,
                "duration_ms": duration_ms,
                "success": True,
                "from_cache": False,
                "timestamp": datetime.now().isoformat()
            }

            # Cache the response (if enabled and not streaming)
            if use_cache and self.cache and not stream:
                self.cache.set(prompt, model.model_id, result, system_prompt)

            return result

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Error generating response: {e}")

            # Update failure stats
            try:
                model_key = next(
                    (k for k, v in self.available_models.items()
                     if model_id and v.model_id == model_id),
                    "unknown"
                )
                if model_key in self.model_stats:
                    self.model_stats[model_key]["failures"] += 1
            except (KeyError, StopIteration):
                pass

            return {
                "content": "",
                "model_name": None,
                "model_id": model_id,
                "task_type": task_type.value,
                "duration_ms": duration_ms,
                "success": False,
                "from_cache": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _generate_with_retry(
        self,
        model: LLMModel,
        messages: List[Dict[str, str]],
        stream: bool,
        temperature: Optional[float],
        max_tokens: Optional[int],
        task_type: TaskType
    ) -> str:
        """Generate response with automatic retry and fallback."""
        last_error = None
        tried_models = set()

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response_text = self.llm_client.chat(
                    model=model.model_id,
                    messages=messages,
                    stream=stream,
                    temperature=temperature or model.temperature,
                    max_tokens=max_tokens or model.max_tokens
                )
                return response_text

            except Exception as e:
                last_error = e
                tried_models.add(model.model_id)

                if attempt < self.retry_config.max_retries:
                    if self.retry_config.should_retry(e):
                        delay = self.retry_config.get_delay(attempt)
                        logger.warning(f"[RETRY] Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                        time.sleep(delay)

                        # Try fallback model on subsequent retries
                        if attempt >= 1:
                            fallback = self._get_fallback_model(task_type, tried_models)
                            if fallback:
                                logger.info(f"[FALLBACK] Switching to fallback model: {fallback.name}")
                                model = fallback
                    else:
                        # Non-retryable error, try fallback immediately
                        fallback = self._get_fallback_model(task_type, tried_models)
                        if fallback:
                            logger.info(f"[FALLBACK] Non-retryable error, switching to: {fallback.name}")
                            model = fallback
                        else:
                            raise

        raise last_error or RuntimeError("All retry attempts exhausted")

    def _get_fallback_model(self, task_type: TaskType, exclude_models: set) -> Optional[LLMModel]:
        """Get a fallback model that hasn't been tried yet."""
        candidates = [
            model for model in self.available_models.values()
            if model.model_id not in exclude_models
        ]

        if not candidates:
            return None

        # Prefer models suited for the task
        task_suited = [m for m in candidates if task_type in m.recommended_tasks]
        if task_suited:
            candidates = task_suited

        # Sort by priority
        candidates.sort(key=lambda m: -m.priority)
        return candidates[0] if candidates else None

    def generate_multiple(
        self,
        prompt: str,
        task_type: TaskType,
        num_models: int = 3,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate responses from multiple models for consensus.

        Args:
            prompt: User prompt
            task_type: Type of task
            num_models: Number of models to use
            system_prompt: System prompt
            temperature: Sampling temperature
            parallel: Execute requests in parallel (faster but uses more resources)

        Returns:
            List of responses from different models
        """
        # Get top N models for task
        candidates = [
            model for model in self.available_models.values()
            if task_type in model.recommended_tasks
        ]

        if not candidates:
            candidates = list(self.available_models.values())

        candidates.sort(key=lambda m: -m.priority)
        selected_models = candidates[:min(num_models, len(candidates))]

        if parallel and len(selected_models) > 1:
            # Execute in parallel using thread pool
            return self._generate_multiple_parallel(
                prompt=prompt,
                task_type=task_type,
                models=selected_models,
                system_prompt=system_prompt,
                temperature=temperature
            )
        else:
            # Sequential execution
            responses = []
            for model in selected_models:
                response = self.generate(
                    prompt=prompt,
                    task_type=task_type,
                    model_id=model.model_id,
                    system_prompt=system_prompt,
                    temperature=temperature
                )
                responses.append(response)
            return responses

    def _generate_multiple_parallel(
        self,
        prompt: str,
        task_type: TaskType,
        models: List[LLMModel],
        system_prompt: Optional[str],
        temperature: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Execute multiple model requests in parallel."""
        futures = []
        responses = []

        for model in models:
            future = self.executor.submit(
                self.generate,
                prompt=prompt,
                task_type=task_type,
                model_id=model.model_id,
                system_prompt=system_prompt,
                temperature=temperature,
                use_cache=True,
                skip_rate_limit=False
            )
            futures.append((model.name, future))

        # Collect results
        for model_name, future in futures:
            try:
                result = future.result(timeout=120)  # 2 minute timeout per model
                responses.append(result)
            except Exception as e:
                logger.error(f"[PARALLEL] Model {model_name} failed: {e}")
                responses.append({
                    "content": "",
                    "model_name": model_name,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        return responses

    async def generate_async(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async version of generate for concurrent operations.

        Use this when you need to make multiple LLM calls concurrently
        from async code.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.generate(
                prompt=prompt,
                task_type=task_type,
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt
            )
        )

    async def generate_multiple_async(
        self,
        prompt: str,
        task_type: TaskType,
        num_models: int = 3,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Async version of generate_multiple for concurrent operations.
        """
        candidates = [
            model for model in self.available_models.values()
            if task_type in model.recommended_tasks
        ]

        if not candidates:
            candidates = list(self.available_models.values())

        candidates.sort(key=lambda m: -m.priority)
        selected_models = candidates[:min(num_models, len(candidates))]

        tasks = [
            self.generate_async(
                prompt=prompt,
                task_type=task_type,
                model_id=model.model_id,
                system_prompt=system_prompt,
                temperature=temperature
            )
            for model in selected_models
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with their configurations."""
        return [
            {
                "key": key,
                "name": model.name,
                "model_id": model.model_id,
                "capabilities": [cap.value for cap in model.capabilities],
                "context_window": model.context_window,
                "recommended_tasks": [task.value for task in model.recommended_tasks],
                "priority": model.priority,
                "stats": self.model_stats.get(key, {})
            }
            for key, model in self.available_models.items()
        ]

    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics for all models."""
        return self.model_stats.copy()

    def reset_stats(self):
        """Reset all model statistics."""
        for key in self.model_stats:
            self.model_stats[key] = {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "total_duration_ms": 0,
                "avg_duration_ms": 0
            }

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status including all production hardening components."""
        status = {
            "models": {
                "available_count": len(self.available_models),
                "models": list(self.available_models.keys())
            },
            "performance": self.get_model_stats()
        }

        # Add cache stats if enabled
        if self.cache:
            status["cache"] = self.cache.get_stats()

        # Add rate limiter status if enabled
        if self.rate_limiter:
            status["rate_limiter"] = self.rate_limiter.get_status()

        # Add retry config
        status["retry_config"] = {
            "max_retries": self.retry_config.max_retries,
            "base_delay": self.retry_config.base_delay,
            "max_delay": self.retry_config.max_delay
        }

        return status

    def clear_cache(self):
        """Clear the response cache."""
        if self.cache:
            self.cache.clear()
            logger.info("[CACHE] Cache cleared")

    def shutdown(self):
        """Shutdown executor and cleanup resources."""
        if self.executor:
            self.executor.shutdown(wait=False)
            logger.info("[SHUTDOWN] Thread pool executor shutdown")


# Global instance
_multi_llm_client: Optional[MultiLLMClient] = None


def get_multi_llm_client() -> MultiLLMClient:
    """Get or create global Multi-LLM client instance."""
    global _multi_llm_client
    if _multi_llm_client is None:
        _multi_llm_client = MultiLLMClient()
    return _multi_llm_client
