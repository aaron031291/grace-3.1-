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
- Failover
- Performance tracking
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests

from ollama_client.client import OllamaClient
from settings import settings

logger = logging.getLogger(__name__)


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

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Multi-LLM client.

        Args:
            base_url: Ollama base URL
        """
        self.ollama_client = OllamaClient(base_url or settings.OLLAMA_URL)
        self.available_models: Dict[str, LLMModel] = {}
        self.model_stats: Dict[str, Dict[str, Any]] = {}

        # Discover available models
        self._discover_models()

    def _discover_models(self):
        """Discover which models are installed and available."""
        try:
            installed_models = self.ollama_client.get_all_models()
            installed_model_names = {model.name for model in installed_models}

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
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response from selected model.

        Args:
            prompt: User prompt
            task_type: Type of task
            model_id: Specific model ID (optional, auto-selects if not provided)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt
            stream: Whether to stream response

        Returns:
            Response dictionary with content and metadata
        """
        start_time = datetime.now()

        try:
            # Select model
            if model_id:
                # Find model by ID
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

            # Prepare messages for chat endpoint
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

            # Generate response
            response_text = self.ollama_client.chat(
                model=model.model_id,
                messages=messages,
                stream=stream,
                temperature=temperature or model.temperature,
                num_predict=max_tokens or model.max_tokens
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Update success stats
            if model_key in self.model_stats:
                stats = self.model_stats[model_key]
                stats["successes"] += 1
                stats["total_duration_ms"] += duration_ms
                stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["successes"]

            return {
                "content": response_text,
                "model_name": model.name,
                "model_id": model.model_id,
                "task_type": task_type.value,
                "duration_ms": duration_ms,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }

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
            except:
                pass

            return {
                "content": "",
                "model_name": None,
                "model_id": model_id,
                "task_type": task_type.value,
                "duration_ms": duration_ms,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def generate_multiple(
        self,
        prompt: str,
        task_type: TaskType,
        num_models: int = 3,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate responses from multiple models for consensus.

        Args:
            prompt: User prompt
            task_type: Type of task
            num_models: Number of models to use
            system_prompt: System prompt
            temperature: Sampling temperature

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


# Global instance
_multi_llm_client: Optional[MultiLLMClient] = None


def get_multi_llm_client() -> MultiLLMClient:
    """Get or create global Multi-LLM client instance."""
    global _multi_llm_client
    if _multi_llm_client is None:
        _multi_llm_client = MultiLLMClient()
    return _multi_llm_client
