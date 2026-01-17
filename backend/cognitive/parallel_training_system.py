"""
Parallel Training System with Sub-Agents and Background Processing

Accelerates Grace's learning by:
1. Parallel processing of multiple files simultaneously
2. Sub-agents for different problem perspectives
3. Background workers for continuous training
4. Resource-aware scheduling and load balancing
"""

import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp

logger = logging.getLogger(__name__)


class TrainingAgentRole(str, Enum):
    """Role of training sub-agent."""
    SYNTAX_SPECIALIST = "syntax_specialist"
    LOGIC_SPECIALIST = "logic_specialist"
    PERFORMANCE_SPECIALIST = "performance_specialist"
    SECURITY_SPECIALIST = "security_specialist"
    ARCHITECTURE_SPECIALIST = "architecture_specialist"
    GENERALIST = "generalist"


@dataclass
class TrainingTask:
    """A training task for a sub-agent."""
    task_id: str
    agent_role: TrainingAgentRole
    file_path: str
    problem_perspective: str
    difficulty_level: int
    priority: int = 5  # 1-10, higher = more important
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


@dataclass
class TrainingAgent:
    """A training sub-agent."""
    agent_id: str
    role: TrainingAgentRole
    specialization: List[str]  # Problem types this agent handles
    max_concurrent_tasks: int = 5  # Max files processed simultaneously
    current_tasks: List[TrainingTask] = field(default_factory=list)
    completed_tasks: List[TrainingTask] = field(default_factory=list)
    success_rate: float = 0.5
    total_tasks: int = 0
    is_active: bool = True


@dataclass
class ResourceConfig:
    """Resource configuration for parallel processing."""
    max_workers: int = None  # None = auto-detect (CPU count)
    max_files_per_agent: int = 10  # Max files processed by one agent simultaneously
    background_workers: int = 2  # Number of background training workers
    task_queue_size: int = 1000  # Max pending tasks
    batch_size: int = 20  # Files processed in parallel per batch


class ParallelTrainingSystem:
    """
    Parallel Training System with Sub-Agents.
    
    Accelerates learning by:
    1. Parallel file processing (multiple files simultaneously)
    2. Specialized sub-agents (different problem perspectives in parallel)
    3. Background workers (continuous training)
    4. Resource-aware scheduling
    """
    
    def __init__(
        self,
        base_training_system,
        resource_config: Optional[ResourceConfig] = None,
        enable_background: bool = True
    ):
        """Initialize Parallel Training System."""
        self.base_system = base_training_system
        self.resource_config = resource_config or ResourceConfig()
        
        # Auto-detect workers if not specified
        if self.resource_config.max_workers is None:
            self.resource_config.max_workers = max(1, mp.cpu_count() - 1)  # Leave 1 CPU free
        
        logger.info(
            f"[PARALLEL-TRAINING] Initialized with {self.resource_config.max_workers} workers, "
            f"{self.resource_config.background_workers} background workers"
        )
        
        # Sub-agents
        self.agents: Dict[str, TrainingAgent] = {}
        self._initialize_agents()
        
        # Task queue
        self.task_queue: queue.Queue = queue.Queue(maxsize=self.resource_config.task_queue_size)
        
        # Worker pool
        self.executor: Optional[ThreadPoolExecutor] = None
        self.background_workers: List[threading.Thread] = []
        self.background_running = False
        
        # Statistics
        self.stats = {
            "total_tasks_queued": 0,
            "total_tasks_completed": 0,
            "total_parallel_executions": 0,
            "average_parallelism": 0.0,
            "peak_parallelism": 0
        }
        
        # Start background workers if enabled
        if enable_background:
            self.start_background_workers()
    
    def _initialize_agents(self):
        """Initialize specialized sub-agents."""
        agent_configs = [
            (TrainingAgentRole.SYNTAX_SPECIALIST, ["syntax_errors"]),
            (TrainingAgentRole.LOGIC_SPECIALIST, ["logic_errors"]),
            (TrainingAgentRole.PERFORMANCE_SPECIALIST, ["performance_issues"]),
            (TrainingAgentRole.SECURITY_SPECIALIST, ["security_vulnerabilities"]),
            (TrainingAgentRole.ARCHITECTURE_SPECIALIST, ["architectural_problems"]),
            (TrainingAgentRole.GENERALIST, ["*"])  # Handles any problem type
        ]
        
        for role, specializations in agent_configs:
            agent = TrainingAgent(
                agent_id=f"agent_{role.value}",
                role=role,
                specialization=specializations,
                max_concurrent_tasks=self.resource_config.max_files_per_agent
            )
            self.agents[agent.agent_id] = agent
        
        logger.info(f"[PARALLEL-TRAINING] Initialized {len(self.agents)} sub-agents")
    
    # ==================== PARALLEL PROCESSING ====================
    
    def process_files_parallel(
        self,
        file_paths: List[str],
        cycle: Any,
        max_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process multiple files in parallel.
        
        Uses ThreadPoolExecutor for concurrent file processing.
        """
        if not file_paths:
            return {"files_fixed": [], "files_failed": [], "total_time": 0.0}
        
        max_workers = max_workers or self.resource_config.max_workers
        
        logger.info(
            f"[PARALLEL-TRAINING] Processing {len(file_paths)} files in parallel "
            f"(workers: {max_workers})"
        )
        
        start_time = time.time()
        results = {"files_fixed": [], "files_failed": [], "knowledge_gained": []}
        
        # Process files in batches to avoid overwhelming system
        batch_size = self.resource_config.batch_size
        batches = [file_paths[i:i+batch_size] for i in range(0, len(file_paths), batch_size)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for batch in batches:
                # Submit batch of tasks
                futures = {
                    executor.submit(self._process_single_file, file_path, cycle): file_path
                    for file_path in batch
                }
                
                # Collect results as they complete
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        result = future.result()
                        
                        if result.get("success"):
                            results["files_fixed"].append(file_path)
                            if result.get("lesson"):
                                results["knowledge_gained"].append(result["lesson"])
                        else:
                            results["files_failed"].append(file_path)
                        
                        self.stats["total_tasks_completed"] += 1
                        self.stats["total_parallel_executions"] += 1
                        
                    except Exception as e:
                        logger.error(f"[PARALLEL-TRAINING] Error processing {file_path}: {e}")
                        results["files_failed"].append(file_path)
        
        elapsed_time = time.time() - start_time
        
        # Update statistics
        parallelism = len(file_paths) / elapsed_time if elapsed_time > 0 else 0
        self.stats["average_parallelism"] = (
            (self.stats["average_parallelism"] * (self.stats["total_tasks_completed"] - len(file_paths)) +
             parallelism * len(file_paths)) / self.stats["total_tasks_completed"]
            if self.stats["total_tasks_completed"] > 0 else parallelism
        )
        self.stats["peak_parallelism"] = max(self.stats["peak_parallelism"], parallelism)
        
        results["total_time"] = elapsed_time
        results["parallelism"] = parallelism
        
        logger.info(
            f"[PARALLEL-TRAINING] Completed {len(results['files_fixed'])}/{len(file_paths)} files "
            f"in {elapsed_time:.2f}s (parallelism: {parallelism:.2f} files/s)"
        )
        
        return results
    
    def _process_single_file(
        self,
        file_path: str,
        cycle: Any
    ) -> Dict[str, Any]:
        """Process a single file (worker function)."""
        try:
            # Use base training system's practice fix method
            result = self.base_system._practice_fix_in_sandbox(file_path, cycle)
            return result
        except Exception as e:
            logger.error(f"[PARALLEL-TRAINING] File processing error for {file_path}: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== SUB-AGENT SYSTEM ====================
    
    def assign_tasks_to_agents(
        self,
        file_paths: List[str],
        cycle: Any
    ) -> Dict[str, List[TrainingTask]]:
        """
        Assign tasks to specialized sub-agents.
        
        Routes files to agents based on problem perspective.
        """
        # Group files by problem perspective
        problem_perspective = cycle.problem_perspective.value if hasattr(cycle, 'problem_perspective') else "general"
        
        # Select appropriate agents
        agents_to_use = self._select_agents_for_perspective(problem_perspective)
        
        # Create tasks
        tasks = []
        for file_path in file_paths:
            task = TrainingTask(
                task_id=f"task_{datetime.utcnow().timestamp()}_{len(tasks)}",
                agent_role=agents_to_use[0].role if agents_to_use else TrainingAgentRole.GENERALIST,
                file_path=file_path,
                problem_perspective=problem_perspective,
                difficulty_level=cycle.difficulty_level if hasattr(cycle, 'difficulty_level') else 1
            )
            tasks.append(task)
        
        # Distribute tasks to agents (load balancing)
        agent_assignments = self._distribute_tasks_to_agents(tasks, agents_to_use)
        
        return agent_assignments
    
    def _select_agents_for_perspective(self, perspective: str) -> List[TrainingAgent]:
        """Select agents best suited for problem perspective."""
        # Find specialized agents
        specialized = []
        for agent in self.agents.values():
            if agent.role != TrainingAgentRole.GENERALIST:
                for spec in agent.specialization:
                    if spec == perspective or spec == "*":
                        specialized.append(agent)
        
        # If no specialized agent, use generalist
        if not specialized:
            specialized = [self.agents.get("agent_generalist")]
        
        return specialized
    
    def _distribute_tasks_to_agents(
        self,
        tasks: List[TrainingTask],
        agents: List[TrainingAgent]
    ) -> Dict[str, List[TrainingTask]]:
        """Distribute tasks to agents (load balancing)."""
        assignments = defaultdict(list)
        
        # Round-robin distribution
        agent_index = 0
        for task in tasks:
            # Skip agents at capacity
            available_agents = [a for a in agents if len(a.current_tasks) < a.max_concurrent_tasks]
            
            if not available_agents:
                # All agents busy, use agent with least current tasks
                agent = min(agents, key=lambda a: len(a.current_tasks))
            else:
                # Use round-robin
                agent = available_agents[agent_index % len(available_agents)]
                agent_index += 1
            
            assignments[agent.agent_id].append(task)
        
        return dict(assignments)
    
    async def process_with_sub_agents(
        self,
        file_paths: List[str],
        cycle: Any
    ) -> Dict[str, Any]:
        """Process files using sub-agents in parallel."""
        # Assign tasks to agents
        assignments = self.assign_tasks_to_agents(file_paths, cycle)
        
        # Process each agent's tasks in parallel
        tasks_per_agent = []
        for agent_id, tasks in assignments.items():
            tasks_per_agent.append(
                self._process_agent_tasks(agent_id, tasks, cycle)
            )
        
        # Wait for all agents to complete
        results_per_agent = await asyncio.gather(*tasks_per_agent)
        
        # Combine results
        combined_results = {
            "files_fixed": [],
            "files_failed": [],
            "knowledge_gained": [],
            "agent_results": {}
        }
        
        for agent_id, agent_results in zip(assignments.keys(), results_per_agent):
            combined_results["files_fixed"].extend(agent_results["files_fixed"])
            combined_results["files_failed"].extend(agent_results["files_failed"])
            combined_results["knowledge_gained"].extend(agent_results.get("knowledge_gained", []))
            combined_results["agent_results"][agent_id] = agent_results
        
        return combined_results
    
    async def _process_agent_tasks(
        self,
        agent_id: str,
        tasks: List[TrainingTask],
        cycle: Any
    ) -> Dict[str, Any]:
        """Process tasks assigned to an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"files_fixed": [], "files_failed": [], "knowledge_gained": []}
        
        # Process agent's tasks in parallel (up to max_concurrent_tasks)
        results = {"files_fixed": [], "files_failed": [], "knowledge_gained": []}
        
        # Process in batches (max concurrent tasks)
        for i in range(0, len(tasks), agent.max_concurrent_tasks):
            batch = tasks[i:i + agent.max_concurrent_tasks]
            
            # Process batch
            batch_results = self.process_files_parallel(
                [task.file_path for task in batch],
                cycle,
                max_workers=min(len(batch), agent.max_concurrent_tasks)
            )
            
            results["files_fixed"].extend(batch_results["files_fixed"])
            results["files_failed"].extend(batch_results["files_failed"])
            results["knowledge_gained"].extend(batch_results.get("knowledge_gained", []))
        
        return results
    
    # ==================== BACKGROUND WORKERS ====================
    
    def start_background_workers(self):
        """Start background workers for continuous training."""
        if self.background_running:
            logger.warning("[PARALLEL-TRAINING] Background workers already running")
            return
        
        self.background_running = True
        
        for i in range(self.resource_config.background_workers):
            worker = threading.Thread(
                target=self._background_worker,
                args=(i,),
                daemon=True,
                name=f"TrainingWorker-{i}"
            )
            worker.start()
            self.background_workers.append(worker)
        
        logger.info(f"[PARALLEL-TRAINING] Started {len(self.background_workers)} background workers")
    
    def stop_background_workers(self):
        """Stop background workers."""
        self.background_running = False
        
        # Wait for workers to finish current tasks
        for worker in self.background_workers:
            worker.join(timeout=5.0)
        
        self.background_workers.clear()
        logger.info("[PARALLEL-TRAINING] Background workers stopped")
    
    def _background_worker(self, worker_id: int):
        """Background worker that continuously processes training tasks."""
        logger.info(f"[PARALLEL-TRAINING] Background worker {worker_id} started")
        
        while self.background_running:
            try:
                # Get task from queue (with timeout)
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue  # No tasks available, check again
                
                # Process task
                try:
                    self._process_background_task(task)
                except Exception as e:
                    logger.error(f"[PARALLEL-TRAINING] Background task error: {e}")
                finally:
                    self.task_queue.task_done()
                    
            except Exception as e:
                logger.error(f"[PARALLEL-TRAINING] Background worker {worker_id} error: {e}")
                time.sleep(1.0)  # Brief pause before retry
        
        logger.info(f"[PARALLEL-TRAINING] Background worker {worker_id} stopped")
    
    def _process_background_task(self, task: TrainingTask):
        """Process a background training task."""
        task.started_at = datetime.utcnow()
        
        # Get cycle (would be stored in task metadata)
        # For now, simulate
        result = self.base_system._practice_fix_in_sandbox(
            task.file_path,
            None  # Would need cycle reference
        )
        
        task.completed_at = datetime.utcnow()
        task.result = result
        
        # Update agent statistics
        agent = self.agents.get(f"agent_{task.agent_role.value}")
        if agent:
            agent.completed_tasks.append(task)
            agent.total_tasks += 1
            
            if result.get("success"):
                # Update success rate (exponential moving average)
                agent.success_rate = 0.9 * agent.success_rate + 0.1 * 1.0
            else:
                agent.success_rate = 0.9 * agent.success_rate + 0.1 * 0.0
    
    # ==================== RESOURCE-AWARE SCHEDULING ====================
    
    def get_resource_utilization(self) -> Dict[str, Any]:
        """Get current resource utilization."""
        total_capacity = sum(agent.max_concurrent_tasks for agent in self.agents.values())
        total_active = sum(len(agent.current_tasks) for agent in self.agents.values())
        queue_size = self.task_queue.qsize()
        
        return {
            "total_capacity": total_capacity,
            "total_active": total_active,
            "utilization_rate": total_active / total_capacity if total_capacity > 0 else 0.0,
            "queue_size": queue_size,
            "available_workers": self.resource_config.max_workers,
            "background_workers_active": len(self.background_workers),
            "stats": self.stats
        }
    
    def optimize_for_speed(self) -> Dict[str, Any]:
        """Optimize system for maximum speed."""
        # Increase parallelism
        cpu_count = mp.cpu_count()
        
        # Use more workers if available
        if self.resource_config.max_workers < cpu_count:
            self.resource_config.max_workers = cpu_count
        
        # Increase batch size
        self.resource_config.batch_size = min(50, cpu_count * 2)
        
        # Increase agent capacity
        for agent in self.agents.values():
            agent.max_concurrent_tasks = min(20, cpu_count)
        
        logger.info(
            f"[PARALLEL-TRAINING] Optimized for speed: "
            f"{self.resource_config.max_workers} workers, "
            f"batch_size={self.resource_config.batch_size}"
        )
        
        return {
            "max_workers": self.resource_config.max_workers,
            "batch_size": self.resource_config.batch_size,
            "agent_capacity": self.agents[list(self.agents.keys())[0]].max_concurrent_tasks if self.agents else 0
        }
    
    # ==================== STATISTICS ====================
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "stats": self.stats,
            "agents": {
                agent_id: {
                    "role": agent.role.value,
                    "total_tasks": agent.total_tasks,
                    "success_rate": agent.success_rate,
                    "current_tasks": len(agent.current_tasks)
                }
                for agent_id, agent in self.agents.items()
            },
            "resource_utilization": self.get_resource_utilization()
        }


def get_parallel_training_system(
    base_training_system,
    resource_config: Optional[ResourceConfig] = None,
    enable_background: bool = True
) -> ParallelTrainingSystem:
    """Factory function to get Parallel Training System."""
    return ParallelTrainingSystem(
        base_training_system=base_training_system,
        resource_config=resource_config,
        enable_background=enable_background
    )
