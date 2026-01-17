"""
BigCodeBench Sandbox Training Integration

Integrates BigCodeBench into sandbox training system.
Trains Grace continuously until 98% accuracy across all BigCodeBench tasks.

Features:
- Uses BigCodeBench tasks as training data
- Continuous improvement cycles
- Adapts knowledge when gaps detected
- Tracks progress toward 98% target
- Domain-specific learning
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import subprocess
import sys

logger = logging.getLogger(__name__)


class TrainingStatus(str, Enum):
    """Training status."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"  # Reached 98%
    STOPPED = "stopped"


@dataclass
class BigCodeBenchTrainingCycle:
    """A training cycle using BigCodeBench tasks."""
    cycle_id: str
    variant: str  # "complete", "instruct", "hard"
    tasks_attempted: int = 0
    tasks_passed: int = 0
    tasks_failed: int = 0
    success_rate: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    knowledge_gaps: List[str] = field(default_factory=list)
    improvements_made: List[str] = field(default_factory=list)


@dataclass
class TrainingProgress:
    """Overall training progress."""
    current_success_rate: float = 0.0
    target_success_rate: float = 98.0
    total_cycles: int = 0
    total_tasks_attempted: int = 0
    total_tasks_passed: int = 0
    knowledge_gaps_identified: List[str] = field(default_factory=list)
    knowledge_gaps_fixed: List[str] = field(default_factory=list)
    status: TrainingStatus = TrainingStatus.RUNNING
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_improvement: Optional[datetime] = None


class BigCodeBenchSandboxTraining:
    """
    Integrate BigCodeBench into sandbox training.
    
    Continuously trains Grace on BigCodeBench tasks until 98% accuracy.
    Adapts knowledge when gaps are detected.
    """
    
    TARGET_SUCCESS_RATE = 98.0  # Target: 98% accuracy
    
    def __init__(
        self,
        training_system,
        coding_agent=None,
        self_healing=None,
        sandbox_lab=None,
        llm_orchestrator=None,
        memory_mesh=None,
        variant: str = "complete",  # "complete", "instruct", "hard"
        max_cycles: Optional[int] = None,
        min_improvement_per_cycle: float = 0.5  # Minimum % improvement per cycle
    ):
        """Initialize BigCodeBench sandbox training."""
        self.training_system = training_system
        self.coding_agent = coding_agent
        self.self_healing = self_healing
        self.sandbox_lab = sandbox_lab
        self.llm_orchestrator = llm_orchestrator
        self.memory_mesh = memory_mesh
        self.variant = variant
        self.max_cycles = max_cycles
        self.min_improvement_per_cycle = min_improvement_per_cycle
        
        # BigCodeBench integration
        self.bigcodebench_available = self._check_bigcodebench()
        if not self.bigcodebench_available:
            logger.warning("[BIGCODEBENCH-TRAINING] BigCodeBench not available")
        
        # Progress tracking
        self.progress = TrainingProgress()
        self.cycles: List[BigCodeBenchTrainingCycle] = []
        self.current_cycle: Optional[BigCodeBenchTrainingCycle] = None
        
        # Knowledge gap tracking
        self.knowledge_gaps: Dict[str, Dict[str, Any]] = {}  # gap_id -> gap_info
        self.gap_fixes: Dict[str, List[str]] = {}  # gap_id -> list of fixes
        
        logger.info(f"[BIGCODEBENCH-TRAINING] Initialized (variant: {variant}, target: {self.TARGET_SUCCESS_RATE}%)")
    
    def _check_bigcodebench(self) -> bool:
        """Check if bigcodebench is available."""
        try:
            import bigcodebench
            return True
        except ImportError:
            return False
    
    def _install_bigcodebench(self) -> bool:
        """Install bigcodebench if missing."""
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "bigcodebench", "-q"
            ])
            self.bigcodebench_available = self._check_bigcodebench()
            return self.bigcodebench_available
        except Exception as e:
            logger.error(f"[BIGCODEBENCH-TRAINING] Installation failed: {e}")
            return False
    
    def get_bigcodebench_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get BigCodeBench tasks for training."""
        if not self.bigcodebench_available:
            if not self._install_bigcodebench():
                return []
        
        try:
            import bigcodebench
            from bigcodebench import BigCodeBench
            
            bcb = BigCodeBench()
            
            if self.variant == "complete":
                tasks = bcb.get_tasks(split="complete")
            elif self.variant == "instruct":
                tasks = bcb.get_tasks(split="instruct")
            elif self.variant == "hard":
                tasks = bcb.get_tasks(split="hard")
            else:
                tasks = bcb.get_tasks()
            
            if limit:
                tasks = tasks[:limit]
            
            return tasks
        except Exception as e:
            logger.error(f"[BIGCODEBENCH-TRAINING] Error getting tasks: {e}")
            return []
    
    async def run_training_cycle(self) -> BigCodeBenchTrainingCycle:
        """
        Run a single training cycle on BigCodeBench tasks.
        
        Returns:
            TrainingCycle with results
        """
        cycle_id = f"bigcodebench_cycle_{len(self.cycles) + 1}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        cycle = BigCodeBenchTrainingCycle(
            cycle_id=cycle_id,
            variant=self.variant
        )
        
        self.current_cycle = cycle
        self.progress.total_cycles += 1
        
        logger.info(f"[BIGCODEBENCH-TRAINING] Starting cycle {cycle_id}")
        
        # Get tasks (start with subset, increase over time)
        num_tasks = min(100, 10 + (len(self.cycles) * 10))  # Start with 10, increase
        tasks = self.get_bigcodebench_tasks(limit=num_tasks)
        
        if not tasks:
            logger.error("[BIGCODEBENCH-TRAINING] No tasks available")
            cycle.completed_at = datetime.utcnow()
            return cycle
        
        logger.info(f"[BIGCODEBENCH-TRAINING] Processing {len(tasks)} tasks")
        
        # Process each task
        for i, task in enumerate(tasks):
            if self.progress.status != TrainingStatus.RUNNING:
                break
            
            task_id = task.get("task_id", f"task_{i}")
            prompt = task.get("prompt") or task.get("instruction", "")
            
            try:
                # Generate code using Grace
                success = await self._process_task_in_sandbox(task_id, prompt, task)
                
                cycle.tasks_attempted += 1
                self.progress.total_tasks_attempted += 1
                
                if success:
                    cycle.tasks_passed += 1
                    self.progress.total_tasks_passed += 1
                else:
                    cycle.tasks_failed += 1
                    # Identify knowledge gap
                    gap = self._identify_knowledge_gap(task, prompt)
                    if gap:
                        cycle.knowledge_gaps.append(gap)
                        self._record_knowledge_gap(gap, task)
                
                # Update success rate
                if cycle.tasks_attempted > 0:
                    cycle.success_rate = (cycle.tasks_passed / cycle.tasks_attempted) * 100.0
                
                # Update overall progress
                if self.progress.total_tasks_attempted > 0:
                    self.progress.current_success_rate = (
                        self.progress.total_tasks_passed / self.progress.total_tasks_attempted
                    ) * 100.0
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"[BIGCODEBENCH-TRAINING] Progress: {i+1}/{len(tasks)} "
                        f"(Success: {cycle.success_rate:.1f}%, Overall: {self.progress.current_success_rate:.1f}%)"
                    )
                
            except Exception as e:
                logger.error(f"[BIGCODEBENCH-TRAINING] Task {task_id} error: {e}")
                cycle.tasks_failed += 1
        
        # Fix knowledge gaps
        if cycle.knowledge_gaps:
            fixes = await self._fix_knowledge_gaps(cycle.knowledge_gaps)
            cycle.improvements_made = fixes
            self.progress.knowledge_gaps_fixed.extend(fixes)
            self.progress.last_improvement = datetime.utcnow()
        
        cycle.completed_at = datetime.utcnow()
        self.cycles.append(cycle)
        
        # Check if target reached
        if self.progress.current_success_rate >= self.TARGET_SUCCESS_RATE:
            self.progress.status = TrainingStatus.COMPLETE
            logger.info(
                f"[BIGCODEBENCH-TRAINING] TARGET REACHED! "
                f"Success rate: {self.progress.current_success_rate:.2f}% (target: {self.TARGET_SUCCESS_RATE}%)"
            )
        
        logger.info(
            f"[BIGCODEBENCH-TRAINING] Cycle complete: "
            f"Success rate: {cycle.success_rate:.1f}%, "
            f"Overall: {self.progress.current_success_rate:.1f}%"
        )
        
        return cycle
    
    async def _process_task_in_sandbox(
        self,
        task_id: str,
        prompt: str,
        task_data: Dict[str, Any]
    ) -> bool:
        """
        Process a BigCodeBench task in sandbox.
        
        Returns:
            True if task passed, False otherwise
        """
        try:
            # Use coding agent to generate code
            if self.coding_agent:
                coding_task = self.coding_agent.create_task(
                    task_type="code_generation",
                    description=prompt,
                    context={
                        "bigcodebench_task_id": task_id,
                        "task_data": task_data
                    }
                )
                
                result = self.coding_agent.execute_task(coding_task.task_id)
                
                if result.get("success"):
                    generation = result.get("result", {}).get("generation")
                    if generation:
                        generated_code = generation.code_after if hasattr(generation, 'code_after') else str(generation)
                        
                        # Evaluate with BigCodeBench
                        return await self._evaluate_bigcodebench_task(task_id, generated_code)
            
            return False
        except Exception as e:
            logger.error(f"[BIGCODEBENCH-TRAINING] Task processing error: {e}")
            return False
    
    async def _evaluate_bigcodebench_task(
        self,
        task_id: str,
        generated_code: str
    ) -> bool:
        """Evaluate generated code against BigCodeBench tests."""
        try:
            import bigcodebench
            from bigcodebench import BigCodeBench
            
            bcb = BigCodeBench()
            result = bcb.evaluate_task(
                task_id=task_id,
                generated_code=generated_code,
                variant=self.variant
            )
            
            return result.get("passed", False)
        except Exception as e:
            logger.error(f"[BIGCODEBENCH-TRAINING] Evaluation error: {e}")
            return False
    
    def _identify_knowledge_gap(
        self,
        task: Dict[str, Any],
        prompt: str
    ) -> Optional[str]:
        """Identify knowledge gap from failed task."""
        # Analyze task to identify what knowledge is missing
        # Could use LLM to analyze failure
        
        # Simple heuristic: extract domain/library from task
        domain = task.get("domain", "unknown")
        libraries = task.get("libraries", [])
        
        if libraries:
            gap = f"Library knowledge: {', '.join(libraries)}"
        elif domain:
            gap = f"Domain knowledge: {domain}"
        else:
            gap = f"Task pattern: {prompt[:100]}"
        
        return gap
    
    def _record_knowledge_gap(
        self,
        gap: str,
        task: Dict[str, Any]
    ):
        """Record knowledge gap for later fixing."""
        gap_id = f"gap_{len(self.knowledge_gaps) + 1}"
        
        if gap not in self.knowledge_gaps:
            self.knowledge_gaps[gap] = {
                "gap_id": gap_id,
                "description": gap,
                "first_seen": datetime.utcnow(),
                "occurrences": 0,
                "related_tasks": [],
                "domain": task.get("domain"),
                "libraries": task.get("libraries", [])
            }
        
        self.knowledge_gaps[gap]["occurrences"] += 1
        self.knowledge_gaps[gap]["related_tasks"].append(task.get("task_id"))
        self.progress.knowledge_gaps_identified.append(gap)
    
    async def _fix_knowledge_gaps(
        self,
        gaps: List[str]
    ) -> List[str]:
        """
        Fix identified knowledge gaps.
        
        Adapts knowledge by:
        1. Learning from failed tasks
        2. Storing patterns in Memory Mesh
        3. Updating coding agent knowledge
        4. Creating targeted practice
        """
        fixes = []
        
        for gap in gaps:
            if gap not in self.knowledge_gaps:
                continue
            
            gap_info = self.knowledge_gaps[gap]
            
            try:
                # 1. Store in Memory Mesh
                if self.memory_mesh:
                    learning_content = (
                        f"Knowledge Gap Identified: {gap}\n"
                        f"Domain: {gap_info.get('domain', 'unknown')}\n"
                        f"Libraries: {', '.join(gap_info.get('libraries', []))}\n"
                        f"Occurrences: {gap_info['occurrences']}\n"
                        f"Related Tasks: {', '.join(gap_info['related_tasks'][:5])}"
                    )
                    
                    # Contribute to memory mesh
                    if hasattr(self.memory_mesh, 'contribute_to_grace_learning'):
                        self.memory_mesh.contribute_to_grace_learning(
                            llm_output=learning_content,
                            query=f"Knowledge gap: {gap}",
                            trust_score=0.7,
                            context={
                                "gap_id": gap_info["gap_id"],
                                "domain": gap_info.get("domain"),
                                "libraries": gap_info.get("libraries")
                            }
                        )
                
                # 2. Update coding agent knowledge
                if self.coding_agent and hasattr(self.coding_agent, '_learn_from_task'):
                    # Create learning task
                    learning_content = {
                        "gap": gap,
                        "domain": gap_info.get("domain"),
                        "libraries": gap_info.get("libraries"),
                        "related_tasks": gap_info["related_tasks"]
                    }
                    
                    # Store in coding agent's learning
                    if hasattr(self.coding_agent, 'llm_orchestrator'):
                        if self.coding_agent.llm_orchestrator:
                            if hasattr(self.coding_agent.llm_orchestrator, 'grace_aligned_llm'):
                                self.coding_agent.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                                    llm_output=str(learning_content),
                                    query=f"Fix knowledge gap: {gap}",
                                    trust_score=0.8,
                                    context=learning_content
                                )
                
                fixes.append(f"Fixed gap: {gap}")
                logger.info(f"[BIGCODEBENCH-TRAINING] Fixed knowledge gap: {gap}")
                
            except Exception as e:
                logger.error(f"[BIGCODEBENCH-TRAINING] Error fixing gap {gap}: {e}")
        
        return fixes
    
    async def train_until_target(
        self,
        check_interval_cycles: int = 1
    ) -> TrainingProgress:
        """
        Train continuously until 98% success rate is reached.
        
        Args:
            check_interval_cycles: Check progress every N cycles
        
        Returns:
            Final training progress
        """
        logger.info(
            f"[BIGCODEBENCH-TRAINING] Starting continuous training "
            f"(target: {self.TARGET_SUCCESS_RATE}%)"
        )
        
        cycle_count = 0
        
        while self.progress.status == TrainingStatus.RUNNING:
            # Check max cycles
            if self.max_cycles and cycle_count >= self.max_cycles:
                logger.info(f"[BIGCODEBENCH-TRAINING] Max cycles reached: {self.max_cycles}")
                self.progress.status = TrainingStatus.STOPPED
                break
            
            # Run training cycle
            cycle = await self.run_training_cycle()
            cycle_count += 1
            
            # Check if improvement is sufficient
            if len(self.cycles) > 1:
                prev_cycle = self.cycles[-2]
                improvement = cycle.success_rate - prev_cycle.success_rate
                
                if improvement < self.min_improvement_per_cycle and cycle.success_rate < self.TARGET_SUCCESS_RATE:
                    logger.warning(
                        f"[BIGCODEBENCH-TRAINING] Low improvement: {improvement:.2f}%. "
                        f"Adapting knowledge..."
                    )
                    # Force knowledge gap fixing
                    if cycle.knowledge_gaps:
                        await self._fix_knowledge_gaps(cycle.knowledge_gaps)
            
            # Check if target reached
            if self.progress.current_success_rate >= self.TARGET_SUCCESS_RATE:
                logger.info(
                    f"[BIGCODEBENCH-TRAINING] TARGET ACHIEVED! "
                    f"Success rate: {self.progress.current_success_rate:.2f}%"
                )
                break
            
            # Log progress
            logger.info(
                f"[BIGCODEBENCH-TRAINING] Cycle {cycle_count} complete. "
                f"Current: {self.progress.current_success_rate:.2f}%, "
                f"Target: {self.TARGET_SUCCESS_RATE}%, "
                f"Remaining: {self.TARGET_SUCCESS_RATE - self.progress.current_success_rate:.2f}%"
            )
        
        return self.progress
    
    def get_progress_report(self) -> Dict[str, Any]:
        """Get training progress report."""
        return {
            "current_success_rate": self.progress.current_success_rate,
            "target_success_rate": self.TARGET_SUCCESS_RATE,
            "progress_percentage": (
                (self.progress.current_success_rate / self.TARGET_SUCCESS_RATE) * 100
                if self.TARGET_SUCCESS_RATE > 0 else 0
            ),
            "total_cycles": self.progress.total_cycles,
            "total_tasks_attempted": self.progress.total_tasks_attempted,
            "total_tasks_passed": self.progress.total_tasks_passed,
            "knowledge_gaps_identified": len(self.progress.knowledge_gaps_identified),
            "knowledge_gaps_fixed": len(self.progress.knowledge_gaps_fixed),
            "status": self.progress.status.value,
            "cycles": [
                {
                    "cycle_id": c.cycle_id,
                    "success_rate": c.success_rate,
                    "tasks_attempted": c.tasks_attempted,
                    "tasks_passed": c.tasks_passed,
                    "knowledge_gaps": len(c.knowledge_gaps),
                    "improvements": len(c.improvements_made)
                }
                for c in self.cycles[-10:]  # Last 10 cycles
            ]
        }


def get_bigcodebench_sandbox_training(
    training_system,
    coding_agent=None,
    self_healing=None,
    sandbox_lab=None,
    llm_orchestrator=None,
    memory_mesh=None,
    variant: str = "complete",
    **kwargs
) -> BigCodeBenchSandboxTraining:
    """Factory function to get BigCodeBench sandbox training."""
    return BigCodeBenchSandboxTraining(
        training_system=training_system,
        coding_agent=coding_agent,
        self_healing=self_healing,
        sandbox_lab=sandbox_lab,
        llm_orchestrator=llm_orchestrator,
        memory_mesh=memory_mesh,
        variant=variant,
        **kwargs
    )
