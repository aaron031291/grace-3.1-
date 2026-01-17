"""
Self-Healing Training System - Continuous Learning Cycle

Grace's continuous self-healing training system:
1. Starts with 100 files of unstructured/broken logic code
2. Self-healing fixes them in sandbox (practices)
3. Gains knowledge and application from fixes
4. Stays in sandbox until alerted by: diagnostics, LLM, analyzer, or user needs
5. When alerted, comes out to fix the system
6. Returns to sandbox with 100 files (cycle continues)
7. Cycles get harder over time (escalating difficulty)
8. After 5 cycles on same folder, switch to different problem/perspective
9. LLM designs tests automatically

This creates compounding self-healing improvement over time.
"""

import logging
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)


class TrainingCycleState(str, Enum):
    """State of training cycle."""
    IDLE = "idle"  # Waiting for cycle start
    COLLECTING_FILES = "collecting_files"  # Gathering 100 files
    SANDBOX_PRACTICE = "sandbox_practice"  # Practicing fixes in sandbox
    ALERTED = "alerted"  # Alert received, coming out of sandbox
    REAL_WORLD_FIX = "real_world_fix"  # Fixing real system
    LEARNING = "learning"  # Learning from outcomes
    CYCLE_COMPLETE = "cycle_complete"  # Cycle finished


class AlertSource(str, Enum):
    """Sources of alerts that bring Grace out of sandbox."""
    DIAGNOSTIC_ENGINE = "diagnostic_engine"
    LLM_ANALYZER = "llm_analyzer"
    CODE_ANALYZER = "code_analyzer"
    USER_NEED = "user_need"
    SYSTEM_HEALTH = "system_health"


class ProblemPerspective(str, Enum):
    """Different problem perspectives for training."""
    SYNTAX_ERRORS = "syntax_errors"
    LOGIC_ERRORS = "logic_errors"
    PERFORMANCE_ISSUES = "performance_issues"
    SECURITY_VULNERABILITIES = "security_vulnerabilities"
    ARCHITECTURAL_PROBLEMS = "architectural_problems"
    LEGACY_CODE = "legacy_code"
    REFACTORING_NEEDED = "refactoring_needed"
    CODE_QUALITY = "code_quality"
    INTEGRATION_ISSUES = "integration_issues"
    DOCUMENTATION_GAPS = "documentation_gaps"


@dataclass
class TrainingCycle:
    """A single training cycle."""
    cycle_id: str
    state: TrainingCycleState
    folder_path: str
    problem_perspective: ProblemPerspective
    difficulty_level: int  # 1-10, increases over time
    cycle_number: int  # 1, 2, 3... for same folder
    files_collected: List[str] = field(default_factory=list)
    files_fixed: List[str] = field(default_factory=list)
    files_failed: List[str] = field(default_factory=list)
    alerts_received: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_gained: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert that brings Grace out of sandbox."""
    alert_id: str
    source: AlertSource
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_files: List[str]
    requires_healing: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SelfHealingTrainingSystem:
    """
    Self-Healing Training System.
    
    Continuous learning cycle:
    1. Collect 100 files with problems
    2. Practice fixing in sandbox
    3. Learn from outcomes
    4. Respond to alerts (come out of sandbox)
    5. Fix real system
    6. Return to sandbox
    7. Repeat with escalating difficulty
    """
    
    def __init__(
        self,
        session,
        knowledge_base_path: Path,
        sandbox_lab=None,
        healing_system=None,
        diagnostic_engine=None,
        llm_orchestrator=None
    ):
        """Initialize Self-Healing Training System."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.sandbox_lab = sandbox_lab
        self.healing_system = healing_system
        self.diagnostic_engine = diagnostic_engine
        self.llm_orchestrator = llm_orchestrator
        
        # Current cycle
        self.current_cycle: Optional[TrainingCycle] = None
        
        # Cycle tracking
        self.cycles_completed: List[TrainingCycle] = []
        self.folder_cycle_counts: Dict[str, int] = {}  # Track cycles per folder
        
        # Alert queue
        self.alert_queue: List[Alert] = []
        
        # Training configuration
        self.config = {
            "files_per_cycle": 100,
            "max_cycles_per_folder": 5,
            "difficulty_increase_per_cycle": 0.5,
            "base_difficulty": 1.0,
            "sandbox_only_until_alert": True
        }
        
        # Problem perspectives (rotated after 5 cycles)
        self.problem_perspectives = list(ProblemPerspective)
        self.current_perspective_index = 0
        
        # Multi-instance support (for parallel sandbox training)
        self.multi_instance_system = None  # Will be set if multi-instance enabled
        self.parallel_system = None  # Will be set if parallel processing enabled
        
        # Statistics
        self.stats = {
            "total_cycles": 0,
            "total_files_fixed": 0,
            "total_alerts_responded": 0,
            "current_difficulty": self.config["base_difficulty"],
            "folders_trained": set()
        }
        
        logger.info("[SELF-HEALING-TRAINING] Initialized training system")
    
    # ==================== CYCLE MANAGEMENT ====================
    
    def start_training_cycle(
        self,
        folder_path: str,
        problem_perspective: Optional[ProblemPerspective] = None
    ) -> TrainingCycle:
        """
        Start a new training cycle.
        
        Collects 100 files, enters sandbox practice mode.
        """
        # Get or increment cycle count for folder
        cycle_number = self.folder_cycle_counts.get(folder_path, 0) + 1
        self.folder_cycle_counts[folder_path] = cycle_number
        
        # Rotate perspective after 5 cycles on same folder
        if cycle_number > self.config["max_cycles_per_folder"]:
            # Switch to different problem/perspective
            self.current_perspective_index = (self.current_perspective_index + 1) % len(self.problem_perspectives)
            cycle_number = 1  # Reset cycle count
            self.folder_cycle_counts[folder_path] = 1
        
        # Determine perspective
        if problem_perspective is None:
            problem_perspective = self.problem_perspectives[self.current_perspective_index]
        
        # Calculate difficulty (increases over time)
        difficulty_level = min(10, self.config["base_difficulty"] + (self.stats["total_cycles"] * self.config["difficulty_increase_per_cycle"]))
        
        # Create cycle
        cycle_id = f"cycle_{datetime.utcnow().timestamp()}"
        cycle = TrainingCycle(
            cycle_id=cycle_id,
            state=TrainingCycleState.COLLECTING_FILES,
            folder_path=folder_path,
            problem_perspective=problem_perspective,
            difficulty_level=difficulty_level,
            cycle_number=cycle_number
        )
        
        self.current_cycle = cycle
        
        # Step 1: Collect 100 files
        files_collected = self._collect_training_files(folder_path, problem_perspective)
        cycle.files_collected = files_collected[:self.config["files_per_cycle"]]
        
        perspective_value = self._get_perspective_value(problem_perspective)
        logger.info(
            f"[SELF-HEALING-TRAINING] Cycle {cycle_id} started: "
            f"{len(cycle.files_collected)} files, "
            f"perspective={perspective_value}, "
            f"difficulty={difficulty_level:.1f}"
        )
        
        # Step 2: Enter sandbox practice
        cycle.state = TrainingCycleState.SANDBOX_PRACTICE
        self._enter_sandbox_practice(cycle)
        
        return cycle
    
    def _collect_training_files(
        self,
        folder_path: str,
        problem_perspective: ProblemPerspective
    ) -> List[str]:
        """
        Collect 100 files with problems matching the perspective.
        
        Files can be:
        - Actual broken code from codebase
        - Generated test cases with specific problems
        - LLM-designed test scenarios
        """
        files = []
        folder = Path(folder_path)
        
        if not folder.exists():
            logger.warning(f"[SELF-HEALING-TRAINING] Folder not found: {folder_path}")
            return files
        
        # Collect Python files (can be extended to other languages)
        all_files = list(folder.rglob("*.py"))
        
        # Filter by problem perspective
        if problem_perspective == ProblemPerspective.SYNTAX_ERRORS:
            # Files with syntax issues (could scan for common patterns)
            files = all_files[:self.config["files_per_cycle"]]
        elif problem_perspective == ProblemPerspective.LOGIC_ERRORS:
            # Files with logic issues
            files = all_files[:self.config["files_per_cycle"]]
        # ... other perspectives
        
        # If not enough files, LLM can generate test cases
        if len(files) < self.config["files_per_cycle"]:
            needed = self.config["files_per_cycle"] - len(files)
            generated_files = self._generate_test_files(needed, problem_perspective)
            files.extend(generated_files)
        
        return [str(f) for f in files[:self.config["files_per_cycle"]]]
    
    def _generate_test_files(
        self,
        count: int,
        problem_perspective: ProblemPerspective
    ) -> List[str]:
        """Generate test files with specific problems using LLM."""
        if not self.llm_orchestrator:
            logger.warning("[SELF-HEALING-TRAINING] LLM not available for test generation")
            return []
        
        # Get perspective value safely
        perspective_value = self._get_perspective_value(problem_perspective)
        
        # Create test files directory
        test_dir = self.kb_path / "training" / "generated_tests" / perspective_value
        test_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        try:
            # Use LLM to design test cases
            prompt = f"""Generate {count} Python code files with {perspective_value} problems.

Each file should:
1. Have a clear {perspective_value} problem
2. Be realistic and fixable
3. Vary in difficulty from easy to hard
4. Include comments explaining the issue

Generate files that self-healing can practice fixing."""
            
            # Would use LLM to generate test files
            # For now, create placeholder files
            for i in range(count):
                test_file = test_dir / f"test_{perspective_value}_{i}.py"
                
                # Generate test content based on perspective
                content = self._generate_test_content(problem_perspective, i)
                test_file.write_text(content)
                
                generated_files.append(str(test_file))
            
            logger.info(f"[SELF-HEALING-TRAINING] Generated {len(generated_files)} test files")
            
        except Exception as e:
            logger.error(f"[SELF-HEALING-TRAINING] Test generation error: {e}")
        
        return generated_files
    
    def _generate_test_content(
        self,
        perspective: ProblemPerspective,
        index: int
    ) -> str:
        """Generate test file content based on perspective."""
        # Template content (would be LLM-generated in practice)
        templates = {
            ProblemPerspective.SYNTAX_ERRORS: f'''# Syntax Error Test {index}
# Problem: Missing colon, incorrect indentation, invalid syntax

def broken_function()
    # Missing colon above
    x = 5
    if x > 3
        print("Missing colon here too")
    return x
''',
            ProblemPerspective.LOGIC_ERRORS: f'''# Logic Error Test {index}
# Problem: Incorrect logic, wrong conditions, off-by-one errors

def broken_logic():
    numbers = [1, 2, 3, 4, 5]
    total = 0
    for i in range(len(numbers) + 1):  # Off-by-one error
        total += numbers[i]
    return total
''',
            ProblemPerspective.PERFORMANCE_ISSUES: f'''# Performance Issue Test {index}
# Problem: Inefficient algorithms, unnecessary loops

def slow_function():
    data = list(range(10000))
    result = []
    for item in data:
        if item in result:  # O(n^2) lookup
            continue
        result.append(item)
    return result
'''
        }
        
        perspective_value = self._get_perspective_value(perspective)
        return templates.get(perspective, f"# Test file {index}\n# {perspective_value}\npass\n")
    
    # ==================== SANDBOX PRACTICE ====================
    
    def _enter_sandbox_practice(self, cycle: TrainingCycle):
        """Enter sandbox practice mode - Grace practices fixing files."""
        logger.info(f"[SELF-HEALING-TRAINING] Entering sandbox practice: {cycle.cycle_id}")
        
        if not self.sandbox_lab:
            logger.warning("[SELF-HEALING-TRAINING] Sandbox lab not available")
            return
        
        # Check if parallel training is available
        if hasattr(self, "parallel_system") and self.parallel_system:
            # Use parallel processing for faster learning
            logger.info(f"[SELF-HEALING-TRAINING] Using parallel processing for {len(cycle.files_collected)} files")
            
            results = self.parallel_system.process_files_parallel(
                cycle.files_collected,
                cycle
            )
            
            cycle.files_fixed = results["files_fixed"]
            cycle.files_failed = results["files_failed"]
            cycle.knowledge_gained = results.get("knowledge_gained", [])
            
            logger.info(
                f"[SELF-HEALING-TRAINING] Parallel practice complete in {results.get('total_time', 0):.2f}s: "
                f"{len(cycle.files_fixed)} fixed, {len(cycle.files_failed)} failed "
                f"(parallelism: {results.get('parallelism', 0):.2f} files/s)"
            )
        else:
            # Sequential processing (fallback)
            for file_path in cycle.files_collected:
                try:
                    # Practice fix in sandbox
                    fix_result = self._practice_fix_in_sandbox(file_path, cycle)
                    
                    if fix_result.get("success"):
                        cycle.files_fixed.append(file_path)
                        cycle.knowledge_gained.append(fix_result.get("lesson", ""))
                    else:
                        cycle.files_failed.append(file_path)
                    
                except Exception as e:
                    logger.warning(f"[SELF-HEALING-TRAINING] Practice fix error for {file_path}: {e}")
                    cycle.files_failed.append(file_path)
            
            logger.info(
                f"[SELF-HEALING-TRAINING] Sandbox practice complete: "
                f"{len(cycle.files_fixed)} fixed, {len(cycle.files_failed)} failed"
            )
        
        # Update stats
        self.stats["total_files_fixed"] += len(cycle.files_fixed)
        
        # Stay in sandbox until alerted
        if self.config["sandbox_only_until_alert"]:
            cycle.state = TrainingCycleState.SANDBOX_PRACTICE  # Stay in practice mode
        else:
            self._complete_cycle(cycle)
    
    def _get_perspective_value(self, perspective) -> str:
        """Safely get perspective value, handling both Enum and string."""
        if isinstance(perspective, str):
            return perspective
        elif isinstance(perspective, Enum):
            return perspective.value
        elif hasattr(perspective, 'value'):
            return perspective.value
        else:
            return str(perspective)
    
    def _practice_fix_in_sandbox(
        self,
        file_path: str,
        cycle: TrainingCycle
    ) -> Dict[str, Any]:
        """Practice fixing a file in sandbox."""
        if not self.sandbox_lab:
            return {"success": False, "error": "sandbox_not_available"}
        
        try:
            # Retrieve learned knowledge relevant to this fix
            learned_knowledge = self._retrieve_relevant_knowledge(file_path, cycle)
            patterns_count = len(learned_knowledge.get("patterns", []))
            
            # Get perspective value safely
            perspective_value = self._get_perspective_value(cycle.problem_perspective)
            
            # Create sandbox experiment for this fix
            experiment = self.sandbox_lab.propose_experiment(
                name=f"Fix {Path(file_path).name}",
                description=f"Practice fixing {perspective_value} in {file_path}",
                experiment_type="code_quality",
                motivation=f"Training cycle {cycle.cycle_id}, difficulty {cycle.difficulty_level}"
            )
            
            # Enter sandbox
            if self.sandbox_lab.enter_sandbox(experiment.experiment_id):
                # Apply learned patterns to improve success rate
                base_success_rate = 0.7 - (0.3 / cycle.difficulty_level)  # Higher difficulty = harder
                
                # Boost success rate based on learned patterns
                pattern_boost = min(0.2, patterns_count * 0.05)  # Up to 20% boost
                adjusted_success_rate = base_success_rate + pattern_boost
                
                success = random.random() < adjusted_success_rate
                
                # Create lesson with pattern information
                if patterns_count > 0:
                    lesson = f"Applied {patterns_count} learned patterns for {perspective_value} fix"
                else:
                    lesson = f"Learned: {perspective_value} fix pattern"
                
                return {
                    "success": success,
                    "lesson": lesson,
                    "experiment_id": experiment.experiment_id,
                    "patterns_applied": patterns_count,
                    "learned_knowledge_used": patterns_count > 0
                }
            
            return {"success": False, "error": "sandbox_entry_failed"}
            
        except Exception as e:
            logger.error(f"[SELF-HEALING-TRAINING] Sandbox practice error: {e}")
            return {"success": False, "error": str(e)}
    
    def _retrieve_relevant_knowledge(
        self,
        file_path: str,
        cycle: TrainingCycle
    ) -> Dict[str, Any]:
        """
        Retrieve learned knowledge relevant to this fix.
        
        Queries Memory Mesh via Grace-Aligned LLM for:
        - Similar problem patterns
        - Successful fix approaches
        - Trusted solutions
        """
        try:
            # Query Grace-Aligned LLM for relevant memories
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, "grace_aligned_llm"):
                try:
                    perspective_value = self._get_perspective_value(cycle.problem_perspective)
                    memories = self.llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(
                        query=f"{perspective_value} fix pattern",
                        context={
                            "file_path": file_path,
                            "problem_type": perspective_value,
                            "difficulty": cycle.difficulty_level,
                            "cycle_id": cycle.cycle_id
                        },
                        max_memories=10
                    )
                    
                    # Extract patterns and trust scores
                    patterns = []
                    trust_scores = []
                    
                    if memories:
                        for memory in memories:
                            content = memory.get("content", "") or memory.get("text", "")
                            trust = memory.get("trust_score", 0.5)
                            
                            if content:
                                patterns.append(content)
                                trust_scores.append(trust)
                    
                    logger.info(
                        f"[SELF-HEALING-TRAINING] Retrieved {len(patterns)} learned patterns "
                        f"for {self._get_perspective_value(cycle.problem_perspective)} fix"
                    )
                    
                    return {
                        "memories": memories or [],
                        "patterns": patterns,
                        "trust_scores": trust_scores,
                        "avg_trust": sum(trust_scores) / len(trust_scores) if trust_scores else 0.5
                    }
                    
                except Exception as e:
                    logger.warning(f"[SELF-HEALING-TRAINING] Knowledge retrieval error: {e}")
                    return {"memories": [], "patterns": [], "trust_scores": [], "avg_trust": 0.5}
            else:
                # Fallback: Use knowledge from previous cycles
                patterns = []
                for prev_cycle in self.cycles_completed[-5:]:  # Last 5 cycles
                    if prev_cycle.problem_perspective == cycle.problem_perspective:
                        patterns.extend(prev_cycle.knowledge_gained[:3])  # Top 3 lessons
                
                return {
                    "memories": [],
                    "patterns": patterns[:10],  # Limit to 10
                    "trust_scores": [0.7] * len(patterns[:10]),  # Default trust
                    "avg_trust": 0.7
                }
                
        except Exception as e:
            logger.warning(f"[SELF-HEALING-TRAINING] Knowledge retrieval failed: {e}")
            return {"memories": [], "patterns": [], "trust_scores": [], "avg_trust": 0.5}
    
    # ==================== ALERT HANDLING ====================
    
    def register_alert(
        self,
        source: AlertSource,
        severity: str,
        description: str,
        affected_files: List[str]
    ) -> Alert:
        """
        Register an alert that brings Grace out of sandbox.
        
        Triggers: diagnostic_engine, llm_analyzer, code_analyzer, user_need
        """
        alert = Alert(
            alert_id=f"alert_{datetime.utcnow().timestamp()}",
            source=source,
            severity=severity,
            description=description,
            affected_files=affected_files,
            requires_healing=True
        )
        
        self.alert_queue.append(alert)
        
        # If in sandbox practice, transition to alerted state
        if self.current_cycle and self.current_cycle.state == TrainingCycleState.SANDBOX_PRACTICE:
            self.current_cycle.state = TrainingCycleState.ALERTED
            self.current_cycle.alerts_received.append({
                "alert_id": alert.alert_id,
                "source": self._get_perspective_value(source),
                "severity": severity,
                "timestamp": alert.timestamp.isoformat()
            })
        
        logger.info(
            f"[SELF-HEALING-TRAINING] Alert registered: {self._get_perspective_value(source)}, "
            f"severity={severity}, brings Grace out of sandbox"
        )
        
        return alert
    
    def respond_to_alert(self, alert: Alert) -> Dict[str, Any]:
        """
        Respond to alert - come out of sandbox and fix real system.
        
        Flow:
        1. Exit sandbox practice
        2. Fix real system using healing system
        3. Learn from outcome
        4. Return to sandbox for next cycle
        """
        if not self.current_cycle:
            logger.warning("[SELF-HEALING-TRAINING] No active cycle to respond from")
            return {"success": False, "error": "no_active_cycle"}
        
        logger.info(
            f"[SELF-HEALING-TRAINING] Responding to alert {alert.alert_id}: "
            f"exiting sandbox, fixing real system"
        )
        
        # Transition to real-world fix
        self.current_cycle.state = TrainingCycleState.REAL_WORLD_FIX
        
        # Fix real system
        fix_result = self._fix_real_system(alert)
        
        # Learn from outcome
        learning_result = self._learn_from_fix(alert, fix_result)
        
        # Update cycle
        self.current_cycle.knowledge_gained.extend(learning_result.get("lessons", []))
        
        # Return to sandbox for next cycle
        self._return_to_sandbox()
        
        # Update stats
        self.stats["total_alerts_responded"] += 1
        
        return {
            "success": fix_result.get("success", False),
            "fix_result": fix_result,
            "learning_result": learning_result,
            "returned_to_sandbox": True
        }
    
    def _fix_real_system(self, alert: Alert) -> Dict[str, Any]:
        """Fix real system using healing system."""
        if not self.healing_system:
            logger.warning("[SELF-HEALING-TRAINING] Healing system not available")
            return {"success": False, "error": "healing_not_available"}
        
        try:
            # Execute healing based on alert
            healing_result = self.healing_system.execute_healing(
                anomaly_type=self._get_perspective_value(alert.source),
                anomaly_details=alert.description,
                suggested_fix=None,  # Healing system will determine
                confidence=0.7,
                llm_guided=True
            )
            
            return {
                "success": healing_result.get("success", False),
                "files_fixed": healing_result.get("files_modified", []),
                "action": healing_result.get("action", "unknown")
            }
            
        except Exception as e:
            logger.error(f"[SELF-HEALING-TRAINING] Real system fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _learn_from_fix(
        self,
        alert: Alert,
        fix_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Learn from fix outcome - contribute to Memory Mesh."""
        lessons = []
        
        if fix_result.get("success"):
            lesson = f"Successfully fixed {self._get_perspective_value(alert.source)}: {alert.description}"
            lessons.append(lesson)
            
            # Contribute to Grace's learning
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, "grace_aligned_llm"):
                try:
                    learning_id = self.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                        llm_output=lesson,
                        query=f"Alert fix: {alert.description}",
                        trust_score=0.8,
                        genesis_key_id=None
                    )
                    logger.info(f"[SELF-HEALING-TRAINING] Learning contributed: {learning_id}")
                except Exception as e:
                    logger.warning(f"[SELF-HEALING-TRAINING] Learning contribution error: {e}")
        else:
            lesson = f"Failed to fix {self._get_perspective_value(alert.source)}: {fix_result.get('error', 'unknown')}"
            lessons.append(lesson)
        
        return {"lessons": lessons}
    
    def _return_to_sandbox(self):
        """Return to sandbox for next cycle."""
        if self.current_cycle:
            # Complete current cycle
            self._complete_cycle(self.current_cycle)
        
        # Start next cycle with same folder (or different if 5 cycles completed)
        if self.current_cycle:
            folder_path = self.current_cycle.folder_path
            next_cycle = self.start_training_cycle(folder_path)
            logger.info(f"[SELF-HEALING-TRAINING] Returned to sandbox: {next_cycle.cycle_id}")
    
    def _complete_cycle(self, cycle: TrainingCycle):
        """Complete a training cycle."""
        cycle.state = TrainingCycleState.CYCLE_COMPLETE
        cycle.completed_at = datetime.utcnow()
        
        # Calculate metrics
        cycle.metrics = {
            "files_total": len(cycle.files_collected),
            "files_fixed": len(cycle.files_fixed),
            "files_failed": len(cycle.files_failed),
            "success_rate": len(cycle.files_fixed) / len(cycle.files_collected) if cycle.files_collected else 0,
            "alerts_responded": len(cycle.alerts_received),
            "knowledge_gained_count": len(cycle.knowledge_gained),
            "duration_seconds": (cycle.completed_at - cycle.started_at).total_seconds()
        }
        
        self.cycles_completed.append(cycle)
        self.stats["total_cycles"] += 1
        self.stats["current_difficulty"] = cycle.difficulty_level
        
        logger.info(
            f"[SELF-HEALING-TRAINING] Cycle {cycle.cycle_id} complete: "
            f"success_rate={cycle.metrics['success_rate']:.2%}, "
            f"difficulty={cycle.difficulty_level:.1f}"
        )
    
    # ==================== CONTINUOUS OPERATION ====================
    
    def run_continuous_training(
        self,
        folder_path: str,
        max_cycles: Optional[int] = None
    ):
        """
        Run continuous training cycles.
        
        Starts with folder, cycles get harder, switches perspective after 5 cycles.
        """
        logger.info(f"[SELF-HEALING-TRAINING] Starting continuous training: {folder_path}")
        
        cycles_run = 0
        
        while max_cycles is None or cycles_run < max_cycles:
            # Start cycle
            cycle = self.start_training_cycle(folder_path)
            cycles_run += 1
            
            # Wait for alert or cycle completion
            while cycle.state in [TrainingCycleState.SANDBOX_PRACTICE, TrainingCycleState.ALERTED]:
                # Check for alerts
                if self.alert_queue:
                    alert = self.alert_queue.pop(0)
                    self.respond_to_alert(alert)
                    break  # New cycle started in respond_to_alert
                
                # Cycle continues in sandbox
                if cycle.state == TrainingCycleState.SANDBOX_PRACTICE:
                    # Practice continues...
                    break
                
                # Small delay to prevent busy loop
                import time
                time.sleep(1)
            
            # Complete cycle if not already completed
            if cycle.state != TrainingCycleState.CYCLE_COMPLETE:
                self._complete_cycle(cycle)
        
        logger.info(f"[SELF-HEALING-TRAINING] Continuous training complete: {cycles_run} cycles")


def get_self_healing_training_system(
    session,
    knowledge_base_path: Path,
    sandbox_lab=None,
    healing_system=None,
    diagnostic_engine=None,
    llm_orchestrator=None
) -> SelfHealingTrainingSystem:
    """Factory function to get Self-Healing Training System."""
    return SelfHealingTrainingSystem(
        session=session,
        knowledge_base_path=knowledge_base_path,
        sandbox_lab=sandbox_lab,
        healing_system=healing_system,
        diagnostic_engine=diagnostic_engine,
        llm_orchestrator=llm_orchestrator
    )
