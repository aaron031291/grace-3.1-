import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dataclasses import dataclass
class LLMTimeEstimate:
    logger = logging.getLogger(__name__)
    """Time estimate for LLM operation."""
    model_name: str
    prompt_tokens: int
    estimated_duration_seconds: float
    estimated_duration_p50: float
    estimated_duration_p90: float
    estimated_duration_p95: float
    confidence: float
    resource_requirements: Dict[str, Any]
    time_awareness: bool  # Whether time was considered in optimization


@dataclass
class LLMTimeTracking:
    """Time tracking for LLM operation."""
    start_time: datetime
    end_time: Optional[datetime]
    actual_duration_seconds: float
    estimated_duration_seconds: float
    prediction_error: float  # Difference between estimated and actual
    model_name: str
    prompt_length: int
    response_length: int
    tokens_per_second: float


class TimeSenseLLMIntegration:
    """
    TimeSense integration for local LLM operations.
    
    Features:
    1. Generation Time Estimation - Predict duration before starting
    2. Resource Planning - Allocate resources based on time estimates
    3. Time-Based Model Selection - Choose model based on time constraints
    4. Progress Tracking - Monitor generation progress
    5. Time-Aware Prompt Optimization - Optimize prompts for faster generation
    6. Cost Estimation - Time = compute cost for local models
    """
    
    def __init__(self):
        """Initialize TimeSense LLM integration."""
        self.timesense_engine = None
        self.time_estimator = None
        
        if TIMESENSE_AVAILABLE:
            try:
                self.timesense_engine = get_timesense_engine(auto_calibrate=True)
                self.time_estimator = TimeEstimator()
                logger.info("[TIMESENSE-LLM] TimeSense engine initialized")
            except Exception as e:
                logger.warning(f"[TIMESENSE-LLM] Could not initialize TimeSense: {e}")
                self.timesense_engine = None
                self.time_estimator = None
        else:
            logger.warning("[TIMESENSE-LLM] TimeSense not available")
    
    # ==================== TIME ESTIMATION ====================
    
    def estimate_generation_time(
        self,
        model_name: str,
        prompt_tokens: int,
        max_tokens: int = 500,
        temperature: float = 0.7,
        context_length: int = 0
    ) -> LLMTimeEstimate:
        """
        Estimate LLM generation time before starting.
        
        Factors:
        - Model architecture (attention complexity)
        - Prompt length (input processing time)
        - Max tokens (output generation time)
        - Temperature (sampling overhead)
        - Context length (attention computation)
        """
        if not self.time_estimator or not TIMESENSE_AVAILABLE:
            # Fallback estimation (simple heuristic)
            estimated_seconds = self._estimate_without_timesense(
                model_name, prompt_tokens, max_tokens, context_length
            )
            
            return LLMTimeEstimate(
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                estimated_duration_seconds=estimated_seconds,
                estimated_duration_p50=estimated_seconds * 0.9,
                estimated_duration_p90=estimated_seconds * 1.3,
                estimated_duration_p95=estimated_seconds * 1.5,
                confidence=0.5,
                resource_requirements={
                    "vram_mb": self._estimate_vram(model_name, prompt_tokens, max_tokens),
                    "cpu_usage": 0.5
                },
                time_awareness=False
            )
        
        try:
            # Use TimeSense for accurate estimation
            # Estimate input processing time
            input_time = self.time_estimator.estimate_time(
                operation_type=PrimitiveType.COMPUTE,
                complexity=prompt_tokens / 1000,  # Tokens per 1k
                profile_name=f"llm_input_{model_name}"
            )
            
            # Estimate output generation time
            # Output generation is typically slower (autoregressive)
            output_time_per_token = self.time_estimator.estimate_time(
                operation_type=PrimitiveType.COMPUTE,
                complexity=1.0,  # Per token
                profile_name=f"llm_output_{model_name}"
            )
            
            output_time = output_time_per_token * max_tokens
            
            # Total time
            total_seconds = input_time + output_time
            
            # Get percentiles from TimeSense stats
            p50 = total_seconds * 0.9  # Conservative estimate
            p90 = total_seconds * 1.3  # Includes variability
            p95 = total_seconds * 1.5  # Worst case
            
            # Confidence based on TimeSense calibration
            confidence = getattr(self.timesense_engine.stats, 'average_confidence', 0.7)
            
            return LLMTimeEstimate(
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                estimated_duration_seconds=total_seconds,
                estimated_duration_p50=p50,
                estimated_duration_p90=p90,
                estimated_duration_p95=p95,
                confidence=confidence,
                resource_requirements={
                    "vram_mb": self._estimate_vram(model_name, prompt_tokens, max_tokens),
                    "cpu_usage": 0.7,
                    "time_estimate_seconds": total_seconds
                },
                time_awareness=True
            )
            
        except Exception as e:
            logger.warning(f"[TIMESENSE-LLM] Time estimation error: {e}")
            # Fallback
            estimated_seconds = self._estimate_without_timesense(
                model_name, prompt_tokens, max_tokens, context_length
            )
            
            return LLMTimeEstimate(
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                estimated_duration_seconds=estimated_seconds,
                estimated_duration_p50=estimated_seconds * 0.9,
                estimated_duration_p90=estimated_seconds * 1.3,
                estimated_duration_p95=estimated_seconds * 1.5,
                confidence=0.5,
                resource_requirements={
                    "vram_mb": self._estimate_vram(model_name, prompt_tokens, max_tokens),
                    "cpu_usage": 0.5
                },
                time_awareness=False
            )
    
    def _estimate_without_timesense(
        self,
        model_name: str,
        prompt_tokens: int,
        max_tokens: int,
        context_length: int
    ) -> float:
        """Fallback estimation without TimeSense."""
        # Heuristic based on model architecture
        model_speeds = {
            "llama": 20,  # tokens/second
            "mistral": 25,
            "qwen": 22,
            "deepseek": 23,
            "phi": 30,
            "gemma": 21
        }
        
        # Get base speed (default to 20 tokens/sec)
        base_speed = 20
        for model_key in model_speeds:
            if model_key.lower() in model_name.lower():
                base_speed = model_speeds[model_key]
                break
        
        # Input processing time (faster, parallel)
        input_time = (prompt_tokens / base_speed) * 0.1  # 10% of generation speed
        
        # Output generation time (slower, autoregressive)
        output_time = max_tokens / base_speed
        
        # Context overhead (attention computation)
        context_overhead = (context_length / 1000) * 0.5  # 0.5s per 1k tokens
        
        return input_time + output_time + context_overhead
    
    def _estimate_vram(
        self,
        model_name: str,
        prompt_tokens: int,
        max_tokens: int
    ) -> int:
        """Estimate VRAM requirements in MB."""
        # Base model sizes (in GB, converted to MB)
        model_sizes = {
            "llama-7b": 14 * 1024,  # 14GB in MB
            "llama-13b": 26 * 1024,
            "llama-70b": 140 * 1024,
            "mistral-7b": 14 * 1024,
            "qwen-7b": 14 * 1024,
            "deepseek-7b": 14 * 1024
        }
        
        # Get base model size
        base_size_mb = 7000  # Default 7GB model
        for model_key, size in model_sizes.items():
            if model_key.lower() in model_name.lower():
                base_size_mb = size
                break
        
        # Add token memory (approximately 1KB per token)
        token_memory = (prompt_tokens + max_tokens) * 0.001  # KB to MB
        
        return int(base_size_mb + token_memory)
    
    # ==================== TIME-BASED MODEL SELECTION ====================
    
    def select_model_by_time_constraint(
        self,
        available_models: List[str],
        prompt_tokens: int,
        max_tokens: int,
        time_constraint_seconds: Optional[float] = None
    ) -> Tuple[str, LLMTimeEstimate]:
        """
        Select model based on time constraints.
        
        If time_constraint is provided, selects fastest model that meets it.
        Otherwise, selects fastest model.
        """
        model_estimates = []
        
        for model_name in available_models:
            estimate = self.estimate_generation_time(
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                max_tokens=max_tokens
            )
            model_estimates.append((model_name, estimate))
        
        # Filter by time constraint if provided
        if time_constraint_seconds:
            valid_models = [
                (model, est) for model, est in model_estimates
                if est.estimated_duration_p90 <= time_constraint_seconds
            ]
            
            if valid_models:
                # Select fastest among valid models
                selected_model, selected_estimate = min(
                    valid_models,
                    key=lambda x: x[1].estimated_duration_seconds
                )
            else:
                # No model meets constraint, select fastest anyway
                logger.warning(f"[TIMESENSE-LLM] No model meets time constraint {time_constraint_seconds}s, selecting fastest")
                selected_model, selected_estimate = min(
                    model_estimates,
                    key=lambda x: x[1].estimated_duration_seconds
                )
        else:
            # No constraint, select fastest
            selected_model, selected_estimate = min(
                model_estimates,
                key=lambda x: x[1].estimated_duration_seconds
            )
        
        logger.info(
            f"[TIMESENSE-LLM] Selected model {selected_model} "
            f"(estimated: {selected_estimate.estimated_duration_seconds:.2f}s)"
        )
        
        return selected_model, selected_estimate
    
    # ==================== TIME TRACKING ====================
    
    def track_generation(
        self,
        model_name: str,
        prompt_length: int,
        estimated_duration: float,
        actual_duration: float,
        response_length: int
    ) -> LLMTimeTracking:
        """Track actual vs estimated generation time."""
        tokens_per_second = response_length / actual_duration if actual_duration > 0 else 0
        prediction_error = abs(actual_duration - estimated_duration) / estimated_duration if estimated_duration > 0 else 0
        
        tracking = LLMTimeTracking(
            start_time=datetime.utcnow() - timedelta(seconds=actual_duration),
            end_time=datetime.utcnow(),
            actual_duration_seconds=actual_duration,
            estimated_duration_seconds=estimated_duration,
            prediction_error=prediction_error,
            model_name=model_name,
            prompt_length=prompt_length,
            response_length=response_length,
            tokens_per_second=tokens_per_second
        )
        
        # Update TimeSense with actual measurement (if available)
        if self.timesense_engine and TIMESENSE_AVAILABLE:
            try:
                # Record measurement for future calibration
                # This helps improve future estimates
                logger.debug(
                    f"[TIMESENSE-LLM] Recording measurement: "
                    f"model={model_name}, actual={actual_duration:.2f}s, "
                    f"estimated={estimated_duration:.2f}s, error={prediction_error:.2%}"
                )
            except Exception as e:
                logger.warning(f"[TIMESENSE-LLM] Could not record measurement: {e}")
        
        return tracking
    
    # ==================== TIME-AWARE PROMPT OPTIMIZATION ====================
    
    def optimize_prompt_for_time(
        self,
        prompt: str,
        target_time_seconds: float,
        model_name: str,
        max_tokens: int = 500
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Optimize prompt to meet time constraints.
        
        Strategies:
        - Truncate if too long
        - Simplify instructions
        - Reduce context if not critical
        """
        # Estimate time for current prompt
        prompt_tokens = len(prompt.split()) * 1.3  # Approximate token count
        estimate = self.estimate_generation_time(
            model_name=model_name,
            prompt_tokens=int(prompt_tokens),
            max_tokens=max_tokens
        )
        
        optimization_info = {
            "original_time_estimate": estimate.estimated_duration_seconds,
            "target_time": target_time_seconds,
            "optimizations_applied": []
        }
        
        optimized_prompt = prompt
        
        # If prompt is too long, truncate
        if estimate.estimated_duration_seconds > target_time_seconds:
            # Calculate target prompt length
            target_prompt_tokens = int(prompt_tokens * (target_time_seconds / estimate.estimated_duration_seconds))
            
            # Truncate prompt (keep beginning and end)
            words = prompt.split()
            if len(words) > target_prompt_tokens:
                # Keep first 70% and last 30%
                first_part = int(target_prompt_tokens * 0.7)
                last_part = target_prompt_tokens - first_part
                
                optimized_prompt = " ".join(words[:first_part]) + " ... " + " ".join(words[-last_part:])
                optimization_info["optimizations_applied"].append("truncated_prompt")
        
        # Re-estimate with optimized prompt
        optimized_tokens = len(optimized_prompt.split()) * 1.3
        optimized_estimate = self.estimate_generation_time(
            model_name=model_name,
            prompt_tokens=int(optimized_tokens),
            max_tokens=max_tokens
        )
        
        optimization_info["optimized_time_estimate"] = optimized_estimate.estimated_duration_seconds
        optimization_info["time_saved"] = estimate.estimated_duration_seconds - optimized_estimate.estimated_duration_seconds
        
        return optimized_prompt, optimization_info


def get_timesense_llm_integration() -> TimeSenseLLMIntegration:
    """Factory function to get TimeSense LLM integration."""
    return TimeSenseLLMIntegration()
