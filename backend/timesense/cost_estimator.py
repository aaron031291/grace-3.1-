import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
logger = logging.getLogger(__name__)

class CostEstimate:
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Cost estimate for an operation."""
    estimated_cost_p50: float  # Typical cost (USD)
    estimated_cost_p95: float  # Worst-case cost (USD)
    estimated_cost_p99: float  # Extreme worst-case (USD)
    currency: str = "USD"
    confidence: float = 0.5
    breakdown: Dict[str, float] = None  # Cost breakdown by resource
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'estimated_cost_p50': self.estimated_cost_p50,
            'estimated_cost_p95': self.estimated_cost_p95,
            'estimated_cost_p99': self.estimated_cost_p99,
            'currency': self.currency,
            'confidence': self.confidence,
            'breakdown': self.breakdown or {}
        }


class TimeBasedCostEstimator:
    """
    Estimates computational costs based on time predictions.
    
    Cost model:
    - CPU time: Base computational cost
    - GPU time: Higher cost for GPU operations
    - Memory: Memory usage cost
    - Storage: Storage I/O cost
    """
    
    # Default cost rates (per hour)
    DEFAULT_CPU_COST_PER_HOUR = 0.05  # $0.05/hour
    DEFAULT_GPU_COST_PER_HOUR = 0.50  # $0.50/hour
    DEFAULT_MEMORY_COST_PER_GB_HOUR = 0.01  # $0.01/GB/hour
    DEFAULT_STORAGE_IO_COST_PER_GB = 0.001  # $0.001/GB
    
    def __init__(
        self,
        cpu_cost_per_hour: float = DEFAULT_CPU_COST_PER_HOUR,
        gpu_cost_per_hour: float = DEFAULT_GPU_COST_PER_HOUR,
        memory_cost_per_gb_hour: float = DEFAULT_MEMORY_COST_PER_GB_HOUR,
        storage_io_cost_per_gb: float = DEFAULT_STORAGE_IO_COST_PER_GB
    ):
        """
        Initialize cost estimator.
        
        Args:
            cpu_cost_per_hour: Cost per CPU hour
            gpu_cost_per_hour: Cost per GPU hour
            memory_cost_per_gb_hour: Cost per GB of memory per hour
            storage_io_cost_per_gb: Cost per GB of storage I/O
        """
        self.cpu_cost_per_hour = cpu_cost_per_hour
        self.gpu_cost_per_hour = gpu_cost_per_hour
        self.memory_cost_per_gb_hour = memory_cost_per_gb_hour
        self.storage_io_cost_per_gb = storage_io_cost_per_gb
        
        logger.info("[COST-ESTIMATOR] Initialized")
    
    def estimate_cost(
        self,
        primitive_type: Optional[PrimitiveType] = None,
        size: float = 1.0,
        model_name: Optional[str] = None,
        requires_gpu: bool = False,
        estimated_time_p50_ms: Optional[float] = None,
        estimated_time_p95_ms: Optional[float] = None,
        estimated_time_p99_ms: Optional[float] = None,
        memory_gb: float = 1.0,
        storage_gb: float = 0.0
    ) -> CostEstimate:
        """
        Estimate cost for an operation.
        
        Args:
            primitive_type: Primitive operation type (for time estimation)
            size: Operation size (for time estimation)
            model_name: Model name (for LLM/embedding operations)
            requires_gpu: Whether operation requires GPU
            estimated_time_p50_ms: Pre-computed p50 time estimate (ms)
            estimated_time_p95_ms: Pre-computed p95 time estimate (ms)
            estimated_time_p99_ms: Pre-computed p99 time estimate (ms)
            memory_gb: Memory usage in GB
            storage_gb: Storage I/O in GB
        
        Returns:
            CostEstimate with cost breakdown
        """
        # Get time estimates if not provided
        if estimated_time_p50_ms is None or estimated_time_p95_ms is None:
            if TIMESENSE_AVAILABLE and primitive_type and predict_time:
                try:
                    prediction = predict_time(primitive_type, size, model_name)
                    if prediction:
                        estimated_time_p50_ms = prediction.p50_ms
                        estimated_time_p95_ms = prediction.p95_ms
                        estimated_time_p99_ms = prediction.p99_ms
                        confidence = prediction.confidence
                    else:
                        # Fallback estimates
                        estimated_time_p50_ms = estimated_time_p50_ms or 1000  # 1 second
                        estimated_time_p95_ms = estimated_time_p95_ms or 5000  # 5 seconds
                        estimated_time_p99_ms = estimated_time_p99_ms or 10000  # 10 seconds
                        confidence = 0.3
                except Exception as e:
                    logger.debug(f"[COST-ESTIMATOR] Time estimation failed: {e}")
                    # Use fallback
                    estimated_time_p50_ms = estimated_time_p50_ms or 1000
                    estimated_time_p95_ms = estimated_time_p95_ms or 5000
                    estimated_time_p99_ms = estimated_time_p99_ms or 10000
                    confidence = 0.3
            else:
                # No time estimation available
                estimated_time_p50_ms = estimated_time_p50_ms or 1000
                estimated_time_p95_ms = estimated_time_p95_ms or 5000
                estimated_time_p99_ms = estimated_time_p99_ms or 10000
                confidence = 0.3
        else:
            confidence = 0.8  # High confidence if times provided
        
        # Convert time to hours
        time_p50_hours = estimated_time_p50_ms / (1000 * 3600)
        time_p95_hours = estimated_time_p95_ms / (1000 * 3600)
        time_p99_hours = estimated_time_p99_ms / (1000 * 3600)
        
        # Calculate CPU cost
        cpu_cost_p50 = time_p50_hours * self.cpu_cost_per_hour
        cpu_cost_p95 = time_p95_hours * self.cpu_cost_per_hour
        cpu_cost_p99 = time_p99_hours * self.cpu_cost_per_hour
        
        # Calculate GPU cost (if required)
        gpu_cost_p50 = 0.0
        gpu_cost_p95 = 0.0
        gpu_cost_p99 = 0.0
        if requires_gpu:
            gpu_cost_p50 = time_p50_hours * self.gpu_cost_per_hour
            gpu_cost_p95 = time_p95_hours * self.gpu_cost_per_hour
            gpu_cost_p99 = time_p99_hours * self.gpu_cost_per_hour
        
        # Calculate memory cost
        memory_cost_p50 = time_p50_hours * memory_gb * self.memory_cost_per_gb_hour
        memory_cost_p95 = time_p95_hours * memory_gb * self.memory_cost_per_gb_hour
        memory_cost_p99 = time_p99_hours * memory_gb * self.memory_cost_per_gb_hour
        
        # Calculate storage I/O cost
        storage_cost = storage_gb * self.storage_io_cost_per_gb
        
        # Total costs
        total_cost_p50 = cpu_cost_p50 + gpu_cost_p50 + memory_cost_p50 + storage_cost
        total_cost_p95 = cpu_cost_p95 + gpu_cost_p95 + memory_cost_p95 + storage_cost
        total_cost_p99 = cpu_cost_p99 + gpu_cost_p99 + memory_cost_p99 + storage_cost
        
        breakdown = {
            'cpu_cost_p50': cpu_cost_p50,
            'cpu_cost_p95': cpu_cost_p95,
            'gpu_cost_p50': gpu_cost_p50,
            'gpu_cost_p95': gpu_cost_p95,
            'memory_cost_p50': memory_cost_p50,
            'memory_cost_p95': memory_cost_p95,
            'storage_cost': storage_cost
        }
        
        return CostEstimate(
            estimated_cost_p50=total_cost_p50,
            estimated_cost_p95=total_cost_p95,
            estimated_cost_p99=total_cost_p99,
            confidence=confidence,
            breakdown=breakdown
        )
    
    def estimate_file_processing_cost(
        self,
        file_size_bytes: int,
        include_embedding: bool = True
    ) -> CostEstimate:
        """
        Estimate cost for file processing pipeline.
        
        Args:
            file_size_bytes: Size of file in bytes
            include_embedding: Whether to include embedding generation
        
        Returns:
            CostEstimate
        """
        from timesense.primitives import PrimitiveType
        
        # Estimate cost for file processing
        return self.estimate_cost(
            primitive_type=PrimitiveType.FILE_PROCESSING if include_embedding else None,
            size=file_size_bytes,
            requires_gpu=include_embedding,  # Embeddings may use GPU
            memory_gb=max(1.0, file_size_bytes / (1024**3))  # At least 1GB
        )
    
    def estimate_llm_cost(
        self,
        num_tokens: int,
        model_name: Optional[str] = None
    ) -> CostEstimate:
        """
        Estimate cost for LLM generation.
        
        Args:
            num_tokens: Number of tokens to generate
            model_name: Model name
        
        Returns:
            CostEstimate
        """
        from timesense.primitives import PrimitiveType
        
        return self.estimate_cost(
            primitive_type=PrimitiveType.LLM_TOKENS_GENERATE,
            size=num_tokens,
            model_name=model_name,
            requires_gpu=True,  # LLM inference uses GPU
            memory_gb=2.0  # Typical LLM memory usage
        )


# Global cost estimator instance
_cost_estimator: Optional[TimeBasedCostEstimator] = None


def get_cost_estimator() -> TimeBasedCostEstimator:
    """Get or create global cost estimator."""
    global _cost_estimator
    if _cost_estimator is None:
        _cost_estimator = TimeBasedCostEstimator()
    return _cost_estimator
