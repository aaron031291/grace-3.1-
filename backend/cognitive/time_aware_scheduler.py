import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
logger = logging.getLogger(__name__)

class TaskPriority(str, Enum):
    """Task priority levels."""
    CRITICAL = "critical"  # Must be done immediately
    HIGH = "high"  # Urgent, deadline approaching
    MEDIUM = "medium"  # Normal priority
    LOW = "low"  # Can wait


@dataclass
class ScheduledTask:
    """A task with time-aware scheduling information."""
    task_id: str
    task_type: str
    priority: TaskPriority
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Time predictions
    estimated_time_ms: Optional[float] = None
    estimated_time_p95_ms: Optional[float] = None
    time_confidence: float = 0.5
    time_human_readable: Optional[str] = None
    
    # Scheduling
    scheduled_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.deadline:
            return False
        return datetime.utcnow() > self.deadline
    
    @property
    def time_until_deadline_seconds(self) -> Optional[float]:
        """Get time until deadline in seconds."""
        if not self.deadline:
            return None
        delta = (self.deadline - datetime.utcnow()).total_seconds()
        return max(0, delta)
    
    @property
    def urgency_score(self) -> float:
        """Calculate urgency score (0-1, higher = more urgent)."""
        if not self.deadline:
            return 0.5  # Medium urgency if no deadline
        
        time_remaining = self.time_until_deadline_seconds
        if time_remaining is None or time_remaining <= 0:
            return 1.0  # Overdue = maximum urgency
        
        # Estimate if we can complete in time
        if self.estimated_time_p95_ms:
            estimated_seconds = self.estimated_time_p95_ms / 1000
            if estimated_seconds > time_remaining:
                return 1.0  # Won't complete in time = urgent
        
        # Urgency inversely proportional to time remaining
        # Less than 1 minute = 1.0, 1 hour = 0.8, 1 day = 0.5
        if time_remaining < 60:
            return 1.0
        elif time_remaining < 3600:
            return 0.8 + (0.2 * (60 / time_remaining))
        elif time_remaining < 86400:
            return 0.5 + (0.3 * (3600 / time_remaining))
        else:
            return 0.5


class TimeAwareTaskScheduler:
    """
    Schedules tasks based on time predictions and deadlines.
    
    Prioritization strategy:
    1. Deadline urgency (critical tasks first)
    2. Estimated completion time (short tasks first for throughput)
    3. Time confidence (high confidence first)
    """
    
    def __init__(self):
        self.task_queue: List[ScheduledTask] = []
        logger.info("[TIME-AWARE-SCHEDULER] Initialized")
    
    def add_task(
        self,
        task_id: str,
        task_type: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        primitive_type: Optional[PrimitiveType] = None,
        size: float = 1.0,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScheduledTask:
        """
        Add a task to the scheduler with time estimation.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task
            priority: Task priority
            deadline: Optional deadline
            primitive_type: Primitive operation type (for time estimation)
            size: Operation size (for time estimation)
            model_name: Model name (for LLM/embedding operations)
            metadata: Additional metadata
        
        Returns:
            ScheduledTask with time estimates
        """
        task = ScheduledTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            deadline=deadline,
            metadata=metadata or {}
        )
        
        # Estimate time if TimeSense available and primitive type provided
        if TIMESENSE_AVAILABLE and primitive_type:
            try:
                from timesense.integration import predict_time
                prediction = predict_time(primitive_type, size, model_name)
                if prediction:
                    task.estimated_time_ms = prediction.p50_ms
                    task.estimated_time_p95_ms = prediction.p95_ms
                    task.time_confidence = prediction.confidence
                    task.time_human_readable = prediction.human_readable()
            except Exception as e:
                logger.debug(f"[TIME-AWARE-SCHEDULER] Time estimation failed: {e}")
        
        self.task_queue.append(task)
        logger.debug(f"[TIME-AWARE-SCHEDULER] Added task {task_id}: {task.time_human_readable or 'no estimate'}")
        
        return task
    
    def prioritize_tasks(
        self,
        strategy: str = "balanced"
    ) -> List[ScheduledTask]:
        """
        Prioritize tasks based on strategy.
        
        Strategies:
        - "deadline": Prioritize by deadline urgency
        - "throughput": Prioritize short tasks first
        - "balanced": Combine deadline and throughput
        - "confidence": Prioritize high-confidence predictions first
        
        Args:
            strategy: Prioritization strategy
        
        Returns:
            Prioritized list of tasks
        """
        if not self.task_queue:
            return []
        
        if strategy == "deadline":
            # Sort by deadline urgency
            return sorted(
                self.task_queue,
                key=lambda t: (
                    t.priority.value if t.priority == TaskPriority.CRITICAL else "z",
                    t.time_until_deadline_seconds or float('inf'),
                    -t.urgency_score
                )
            )
        
        elif strategy == "throughput":
            # Sort by estimated time (shortest first)
            return sorted(
                self.task_queue,
                key=lambda t: (
                    t.estimated_time_ms or float('inf'),
                    -t.time_confidence  # Higher confidence first
                )
            )
        
        elif strategy == "confidence":
            # Sort by time prediction confidence
            return sorted(
                self.task_queue,
                key=lambda t: (
                    -t.time_confidence,  # Higher confidence first
                    t.estimated_time_ms or float('inf')
                )
            )
        
        else:  # balanced (default)
            # Combine deadline urgency and time efficiency
            return sorted(
                self.task_queue,
                key=lambda t: (
                    # Critical priority first
                    t.priority.value if t.priority == TaskPriority.CRITICAL else "z",
                    # Then by urgency (inverse - more urgent = lower sort key)
                    -t.urgency_score,
                    # Then by estimated time (shorter first)
                    t.estimated_time_ms or float('inf'),
                    # Finally by confidence (higher first)
                    -t.time_confidence
                )
            )
    
    def get_next_task(self, strategy: str = "balanced") -> Optional[ScheduledTask]:
        """
        Get the next task to execute based on prioritization.
        
        Args:
            strategy: Prioritization strategy
        
        Returns:
            Next task or None if queue is empty
        """
        prioritized = self.prioritize_tasks(strategy)
        if not prioritized:
            return None
        
        task = prioritized[0]
        task.actual_start = datetime.utcnow()
        return task
    
    def complete_task(self, task_id: str, actual_time_ms: Optional[float] = None):
        """Mark task as completed."""
        task = next((t for t in self.task_queue if t.task_id == task_id), None)
        if task:
            task.actual_completion = datetime.utcnow()
            if actual_time_ms:
                task.metadata['actual_time_ms'] = actual_time_ms
                # Log prediction accuracy
                if task.estimated_time_ms:
                    error_ratio = abs(actual_time_ms - task.estimated_time_ms) / task.estimated_time_ms
                    task.metadata['time_prediction_error'] = error_ratio
            self.task_queue.remove(task)
            logger.debug(f"[TIME-AWARE-SCHEDULER] Completed task {task_id}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the task queue."""
        if not self.task_queue:
            return {
                'total_tasks': 0,
                'avg_estimated_time_ms': 0,
                'avg_time_confidence': 0,
                'urgent_tasks': 0
            }
        
        total_time = sum(t.estimated_time_ms or 0 for t in self.task_queue)
        total_confidence = sum(t.time_confidence for t in self.task_queue)
        urgent_count = sum(1 for t in self.task_queue if t.urgency_score > 0.8)
        
        return {
            'total_tasks': len(self.task_queue),
            'avg_estimated_time_ms': total_time / len(self.task_queue) if self.task_queue else 0,
            'avg_time_confidence': total_confidence / len(self.task_queue),
            'urgent_tasks': urgent_count,
            'overdue_tasks': sum(1 for t in self.task_queue if t.is_overdue),
            'total_estimated_time_ms': total_time
        }


# Global scheduler instance
_time_aware_scheduler: Optional[TimeAwareTaskScheduler] = None


def get_time_aware_scheduler() -> TimeAwareTaskScheduler:
    """Get or create global time-aware scheduler."""
    global _time_aware_scheduler
    if _time_aware_scheduler is None:
        _time_aware_scheduler = TimeAwareTaskScheduler()
    return _time_aware_scheduler
