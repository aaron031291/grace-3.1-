import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
logger = logging.getLogger(__name__)

class AgentLoadInfo:
    """Information about an agent's current load."""
    agent_id: str
    current_tasks: int
    max_concurrent: int
    queue_estimated_time_ms: float = 0.0
    capabilities: Dict[str, Any] = field(default_factory=dict)


class TimeAwareLoadBalancer:
    """
    Balances workload across multiple agents based on time predictions.
    
    Assignment strategy:
    1. Estimate time for task on each agent
    2. Consider agent's current queue time
    3. Assign to agent with shortest total completion time
    """
    
    def __init__(self):
        self.agent_loads: Dict[str, AgentLoadInfo] = {}
        logger.info("[TIME-AWARE-LB] Initialized")
    
    def register_agent(
        self,
        agent_id: str,
        max_concurrent: int = 2,
        capabilities: Optional[Dict[str, Any]] = None
    ):
        """Register an agent for load balancing."""
        self.agent_loads[agent_id] = AgentLoadInfo(
            agent_id=agent_id,
            current_tasks=0,
            max_concurrent=max_concurrent,
            capabilities=capabilities or {}
        )
        logger.debug(f"[TIME-AWARE-LB] Registered agent: {agent_id}")
    
    def get_agent_load(self, agent_id: str) -> Optional[AgentLoadInfo]:
        """Get load information for an agent."""
        return self.agent_loads.get(agent_id)
    
    def assign_task(
        self,
        task: Any,  # LearningTask or similar
        agents: List[str],
        task_type: Optional[str] = None,
        task_size: float = 1.0,
        primitive_type: Optional[PrimitiveType] = None
    ) -> str:
        """
        Assign a task to the optimal agent based on time predictions.
        
        Args:
            task: Task to assign
            agents: List of available agent IDs
            task_type: Type of task (for time estimation)
            task_size: Size/complexity of task (for time estimation)
            primitive_type: Primitive operation type (for time estimation)
        
        Returns:
            Selected agent_id
        """
        if not agents:
            raise ValueError("No agents available for task assignment")
        
        # If only one agent, assign to it
        if len(agents) == 1:
            agent_id = agents[0]
            self._update_agent_load(agent_id, increment=True)
            return agent_id
        
        # Get time estimates for each agent
        agent_estimates = []
        
        for agent_id in agents:
            agent_load = self.agent_loads.get(agent_id)
            if not agent_load:
                # Agent not registered, skip
                continue
            
            # Check if agent has capacity
            if agent_load.current_tasks >= agent_load.max_concurrent:
                # Agent at capacity, assign large estimated time
                agent_estimates.append((agent_id, float('inf')))
                continue
            
            # Estimate time for this task on this agent
            task_estimated_ms = self._estimate_task_time(
                task_type=task_type,
                task_size=task_size,
                primitive_type=primitive_type,
                agent_capabilities=agent_load.capabilities
            )
            
            # Total time = queue time + task time
            total_time_ms = agent_load.queue_estimated_time_ms + task_estimated_ms
            
            agent_estimates.append((agent_id, total_time_ms))
        
        if not agent_estimates:
            # No valid agents, assign to first available
            agent_id = agents[0]
            self._update_agent_load(agent_id, increment=True)
            return agent_id
        
        # Select agent with shortest total time
        agent_id = min(agent_estimates, key=lambda x: x[1])[0]
        self._update_agent_load(agent_id, increment=True, estimated_time_ms=task_estimated_ms)
        
        logger.debug(
            f"[TIME-AWARE-LB] Assigned task to {agent_id} "
            f"(estimated={task_estimated_ms:.0f}ms, "
            f"queue_time={self.agent_loads[agent_id].queue_estimated_time_ms:.0f}ms)"
        )
        
        return agent_id
    
    def _estimate_task_time(
        self,
        task_type: Optional[str] = None,
        task_size: float = 1.0,
        primitive_type: Optional[PrimitiveType] = None,
        agent_capabilities: Optional[Dict[str, Any]] = None
    ) -> float:
        """Estimate time for a task."""
        
        # Use TimeSense if primitive type provided
        if TIMESENSE_AVAILABLE and primitive_type and predict_time:
            try:
                prediction = predict_time(primitive_type, task_size)
                if prediction:
                    # Use p95 for worst-case estimation
                    return prediction.p95_ms
            except Exception as e:
                logger.debug(f"[TIME-AWARE-LB] Time estimation failed: {e}")
        
        # Fallback: rough estimates based on task type
        if task_type:
            type_estimates = {
                'study': 30000,  # 30 seconds
                'practice': 60000,  # 1 minute
                'consolidate': 45000,  # 45 seconds
                'mirror': 90000,  # 1.5 minutes
                'file_processing': 15000 * task_size,  # Scale with size
            }
            return type_estimates.get(task_type, 30000)
        
        # Default: 30 seconds
        return 30000
    
    def _update_agent_load(
        self,
        agent_id: str,
        increment: bool = True,
        estimated_time_ms: float = 0.0
    ):
        """Update agent load tracking."""
        if agent_id not in self.agent_loads:
            return
        
        agent_load = self.agent_loads[agent_id]
        
        if increment:
            agent_load.current_tasks += 1
            agent_load.queue_estimated_time_ms += estimated_time_ms
        else:
            # Decrement (task completed)
            agent_load.current_tasks = max(0, agent_load.current_tasks - 1)
            agent_load.queue_estimated_time_ms = max(
                0.0,
                agent_load.queue_estimated_time_ms - estimated_time_ms
            )
    
    def task_completed(self, agent_id: str, actual_time_ms: Optional[float] = None):
        """Notify that a task has been completed."""
        if agent_id not in self.agent_loads:
            return
        
        # Use actual time if provided, otherwise use estimate
        time_ms = actual_time_ms or 0.0
        
        # Update queue time (subtract estimated, add actual if different)
        agent_load = self.agent_loads[agent_id]
        if actual_time_ms and actual_time_ms > 0:
            # Recalibrate: subtract old estimate, but we don't track individual estimates
            # Just decrement by average or actual
            pass
        
        self._update_agent_load(agent_id, increment=False, estimated_time_ms=time_ms)
    
    def get_load_stats(self) -> Dict[str, Any]:
        """Get load balancing statistics."""
        if not self.agent_loads:
            return {
                'total_agents': 0,
                'avg_load': 0.0,
                'max_load': 0,
                'total_queue_time_ms': 0.0
            }
        
        loads = [a.current_tasks for a in self.agent_loads.values()]
        queue_times = [a.queue_estimated_time_ms for a in self.agent_loads.values()]
        
        return {
            'total_agents': len(self.agent_loads),
            'avg_load': sum(loads) / len(loads) if loads else 0.0,
            'max_load': max(loads) if loads else 0,
            'min_load': min(loads) if loads else 0,
            'total_queue_time_ms': sum(queue_times),
            'avg_queue_time_ms': sum(queue_times) / len(queue_times) if queue_times else 0.0,
            'agent_loads': {
                agent_id: {
                    'current_tasks': load.current_tasks,
                    'max_concurrent': load.max_concurrent,
                    'queue_time_ms': load.queue_estimated_time_ms,
                    'utilization': load.current_tasks / load.max_concurrent if load.max_concurrent > 0 else 0.0
                }
                for agent_id, load in self.agent_loads.items()
            }
        }


# Global load balancer instance
_time_aware_load_balancer: Optional[TimeAwareLoadBalancer] = None


def get_time_aware_load_balancer() -> TimeAwareLoadBalancer:
    """Get or create global time-aware load balancer."""
    global _time_aware_load_balancer
    if _time_aware_load_balancer is None:
        _time_aware_load_balancer = TimeAwareLoadBalancer()
    return _time_aware_load_balancer
