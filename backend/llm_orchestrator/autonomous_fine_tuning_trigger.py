"""
Autonomous Fine-Tuning Trigger System

Automatically triggers fine-tuning when:
- Enough high-trust learning examples accumulate
- Performance metrics indicate improvement opportunity
- Code patterns suggest specialization would help
- User performance feedback shows gaps

This makes LLMs continuously improve without manual intervention.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
import time

from .multi_llm_client import MultiLLMClient, TaskType
from .fine_tuning import LLMFineTuningSystem, FineTuningMethod
from .repo_access import RepositoryAccessLayer
from .learning_integration import LearningIntegration

logger = logging.getLogger(__name__)


class TriggerReason(Enum):
    """Reasons for triggering fine-tuning."""
    ENOUGH_EXAMPLES = "enough_examples"  # Accumulated enough high-trust examples
    PERFORMANCE_GAP = "performance_gap"  # Performance metrics show improvement opportunity
    CODE_PATTERN = "code_pattern"  # Code patterns suggest specialization needed
    USER_FEEDBACK = "user_feedback"  # User feedback indicates gaps
    CONTINUOUS_IMPROVEMENT = "continuous_improvement"  # Scheduled continuous improvement


@dataclass
class FineTuningTrigger:
    """Fine-tuning trigger decision."""
    trigger_id: str
    reason: TriggerReason
    task_type: str
    dataset_size: int
    avg_trust_score: float
    estimated_improvement: float
    confidence: float
    should_trigger: bool
    recommendation: str
    timestamp: datetime


class AutonomousFineTuningTrigger:
    """
    Automatically triggers fine-tuning when conditions are met.
    
    Monitors:
    - Learning example accumulation
    - Performance metrics
    - Code patterns
    - User feedback
    - Continuous improvement schedule
    """
    
    def __init__(
        self,
        multi_llm_client: Optional[MultiLLMClient] = None,
        fine_tuning_system: Optional[LLMFineTuningSystem] = None,
        repo_access: Optional[RepositoryAccessLayer] = None,
        learning_integration: Optional[LearningIntegration] = None,
        check_interval_seconds: int = 3600,  # Check every hour
        min_examples_for_trigger: int = 500,
        min_trust_score: float = 0.8,
        auto_approve: bool = False  # If True, auto-approves (use with caution)
    ):
        """
        Initialize autonomous fine-tuning trigger.
        
        Args:
            multi_llm_client: Multi-LLM client
            fine_tuning_system: Fine-tuning system
            repo_access: Repository access
            learning_integration: Learning integration
            check_interval_seconds: How often to check for triggers
            min_examples_for_trigger: Minimum examples needed to trigger
            min_trust_score: Minimum trust score for examples
            auto_approve: If True, automatically approves fine-tuning (dangerous!)
        """
        self.multi_llm = multi_llm_client
        self.fine_tuning = fine_tuning_system
        self.repo_access = repo_access
        self.learning_integration = learning_integration
        
        self.check_interval = check_interval_seconds
        self.min_examples = min_examples_for_trigger
        self.min_trust = min_trust_score
        self.auto_approve = auto_approve
        
        # Monitoring thread
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Trigger history
        self.trigger_history: List[FineTuningTrigger] = []
        
        # Task type tracking
        self.task_type_stats: Dict[str, Dict[str, Any]] = {}
    
    def start_monitoring(self):
        """Start background monitoring for fine-tuning triggers."""
        if self.running:
            logger.warning("[AUTO-FINE-TUNE] Already monitoring")
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="AutoFineTuneMonitor"
        )
        self.monitoring_thread.start()
        logger.info("[AUTO-FINE-TUNE] Started monitoring for fine-tuning triggers")
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("[AUTO-FINE-TUNE] Stopped monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                self.check_and_trigger()
            except Exception as e:
                logger.error(f"[AUTO-FINE-TUNE] Error in monitoring loop: {e}")
            
            # Sleep until next check
            time.sleep(self.check_interval)
    
    def check_and_trigger(self) -> List[FineTuningTrigger]:
        """
        Check all conditions and trigger fine-tuning if appropriate.
        
        Returns:
            List of trigger decisions
        """
        triggers = []
        
        # Check 1: Enough examples accumulated
        example_triggers = self._check_example_accumulation()
        triggers.extend(example_triggers)
        
        # Check 2: Performance gaps
        performance_triggers = self._check_performance_gaps()
        triggers.extend(performance_triggers)
        
        # Check 3: Code patterns
        code_triggers = self._check_code_patterns()
        triggers.extend(code_triggers)
        
        # Check 4: Continuous improvement schedule
        schedule_triggers = self._check_continuous_improvement()
        triggers.extend(schedule_triggers)
        
        # Execute triggers
        for trigger in triggers:
            if trigger.should_trigger:
                self._execute_trigger(trigger)
            
            self.trigger_history.append(trigger)
        
        return triggers
    
    def _check_example_accumulation(self) -> List[FineTuningTrigger]:
        """Check if enough high-trust examples have accumulated."""
        triggers = []
        
        if not self.repo_access:
            return triggers
        
        # Check for each task type
        task_types = ["code_generation", "code_review", "reasoning", "general"]
        
        for task_type in task_types:
            examples = self.repo_access.get_learning_examples(
                min_trust_score=self.min_trust,
                example_type=task_type,
                limit=self.min_examples + 100  # Get a bit more to check
            )
            
            if len(examples) >= self.min_examples:
                avg_trust = sum(ex.get("trust_score", 0) for ex in examples) / len(examples)
                
                # Use LLM to evaluate if fine-tuning would help
                evaluation = self._evaluate_fine_tuning_benefit(
                    task_type=task_type,
                    num_examples=len(examples),
                    avg_trust=avg_trust
                )
                
                trigger = FineTuningTrigger(
                    trigger_id=f"trigger_{datetime.now().timestamp()}",
                    reason=TriggerReason.ENOUGH_EXAMPLES,
                    task_type=task_type,
                    dataset_size=len(examples),
                    avg_trust_score=avg_trust,
                    estimated_improvement=evaluation.get("estimated_improvement", 0.0),
                    confidence=evaluation.get("confidence", 0.0),
                    should_trigger=evaluation.get("should_trigger", False),
                    recommendation=evaluation.get("recommendation", ""),
                    timestamp=datetime.now()
                )
                
                triggers.append(trigger)
        
        return triggers
    
    def _check_performance_gaps(self) -> List[FineTuningTrigger]:
        """Check if performance metrics indicate improvement opportunity."""
        triggers = []
        
        if not self.multi_llm:
            return triggers
        
        # Get model performance stats
        stats = self.multi_llm.get_model_stats()
        
        for model_key, model_stats in stats.items():
            success_rate = 0.0
            if model_stats.get("requests", 0) > 0:
                success_rate = model_stats.get("successes", 0) / model_stats.get("requests", 1)
            
            # If success rate is low, fine-tuning might help
            if success_rate < 0.85 and model_stats.get("requests", 0) > 100:
                # Determine task type from model
                task_type = self._infer_task_type_from_model(model_key)
                
                evaluation = self._evaluate_fine_tuning_benefit(
                    task_type=task_type,
                    num_examples=0,  # Will check separately
                    avg_trust=0.0,
                    performance_context={
                        "success_rate": success_rate,
                        "requests": model_stats.get("requests", 0)
                    }
                )
                
                if evaluation.get("should_trigger", False):
                    trigger = FineTuningTrigger(
                        trigger_id=f"trigger_{datetime.now().timestamp()}",
                        reason=TriggerReason.PERFORMANCE_GAP,
                        task_type=task_type,
                        dataset_size=0,
                        avg_trust_score=0.0,
                        estimated_improvement=evaluation.get("estimated_improvement", 0.0),
                        confidence=evaluation.get("confidence", 0.0),
                        should_trigger=True,
                        recommendation=evaluation.get("recommendation", ""),
                        timestamp=datetime.now()
                    )
                    triggers.append(trigger)
        
        return triggers
    
    def _check_code_patterns(self) -> List[FineTuningTrigger]:
        """Check if code patterns suggest specialization would help."""
        triggers = []
        
        if not self.repo_access:
            return triggers
        
        # Analyze codebase for patterns that suggest fine-tuning opportunities
        # This is a simplified version - in production, use more sophisticated analysis
        
        # Check for code generation patterns
        code_files = self.repo_access.search_code(
            pattern="def.*generate|class.*Generator",
            file_pattern="*.py",
            max_results=20
        )
        
        if len(code_files) > 10:
            # High code generation activity - fine-tuning could help
            evaluation = self._evaluate_fine_tuning_benefit(
                task_type="code_generation",
                num_examples=0,
                avg_trust=0.0,
                code_context={"code_generation_files": len(code_files)}
            )
            
            if evaluation.get("should_trigger", False):
                trigger = FineTuningTrigger(
                    trigger_id=f"trigger_{datetime.now().timestamp()}",
                    reason=TriggerReason.CODE_PATTERN,
                    task_type="code_generation",
                    dataset_size=0,
                    avg_trust_score=0.0,
                    estimated_improvement=evaluation.get("estimated_improvement", 0.0),
                    confidence=evaluation.get("confidence", 0.0),
                    should_trigger=True,
                    recommendation=evaluation.get("recommendation", ""),
                    timestamp=datetime.now()
                )
                triggers.append(trigger)
        
        return triggers
    
    def _check_continuous_improvement(self) -> List[FineTuningTrigger]:
        """Check continuous improvement schedule (e.g., weekly fine-tuning)."""
        triggers = []
        
        # Check if it's been a while since last fine-tuning
        if self.trigger_history:
            last_trigger = max(self.trigger_history, key=lambda t: t.timestamp)
            days_since = (datetime.now() - last_trigger.timestamp).days
            
            # If it's been 7+ days, consider continuous improvement
            if days_since >= 7:
                # Check if we have enough examples for any task type
                if self.repo_access:
                    examples = self.repo_access.get_learning_examples(
                        min_trust_score=self.min_trust,
                        limit=self.min_examples
                    )
                    
                    if len(examples) >= self.min_examples:
                        # Find most common task type
                        task_type = "general"  # Default
                        
                        evaluation = self._evaluate_fine_tuning_benefit(
                            task_type=task_type,
                            num_examples=len(examples),
                            avg_trust=sum(ex.get("trust_score", 0) for ex in examples) / len(examples) if examples else 0.0
                        )
                        
                        if evaluation.get("should_trigger", False):
                            trigger = FineTuningTrigger(
                                trigger_id=f"trigger_{datetime.now().timestamp()}",
                                reason=TriggerReason.CONTINUOUS_IMPROVEMENT,
                                task_type=task_type,
                                dataset_size=len(examples),
                                avg_trust_score=sum(ex.get("trust_score", 0) for ex in examples) / len(examples) if examples else 0.0,
                                estimated_improvement=evaluation.get("estimated_improvement", 0.0),
                                confidence=evaluation.get("confidence", 0.0),
                                should_trigger=True,
                                recommendation=evaluation.get("recommendation", ""),
                                timestamp=datetime.now()
                            )
                            triggers.append(trigger)
        
        return triggers
    
    def _evaluate_fine_tuning_benefit(
        self,
        task_type: str,
        num_examples: int,
        avg_trust: float,
        performance_context: Optional[Dict[str, Any]] = None,
        code_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use LLM to evaluate if fine-tuning would be beneficial."""
        if not self.multi_llm:
            return {
                "should_trigger": False,
                "estimated_improvement": 0.0,
                "confidence": 0.0,
                "recommendation": "Cannot evaluate - LLM not available"
            }
        
        context_parts = []
        if performance_context:
            context_parts.append(f"Performance: {performance_context}")
        if code_context:
            context_parts.append(f"Code patterns: {code_context}")
        
        evaluation_prompt = f"""Evaluate if fine-tuning would be beneficial for this scenario.

Task Type: {task_type}
Number of Examples: {num_examples}
Average Trust Score: {avg_trust:.2f}
{chr(10).join(context_parts) if context_parts else ""}

Questions:
1. Would fine-tuning improve performance for this task type?
2. What estimated improvement percentage? (0-50%)
3. How confident are you? (0.0-1.0)
4. Should we trigger fine-tuning? (Yes/No)

Respond in format:
SHOULD_TRIGGER: Yes/No
ESTIMATED_IMPROVEMENT: X%
CONFIDENCE: 0.X
RECOMMENDATION: Your reasoning"""
        
        response = self.multi_llm.generate(
            prompt=evaluation_prompt,
            task_type=TaskType.REASONING,
            system_prompt="You evaluate fine-tuning opportunities based on data quality, quantity, and performance metrics."
        )
        
        # Parse response
        content = response.get("content", "")
        should_trigger = "SHOULD_TRIGGER: Yes" in content or "should trigger: yes" in content.lower()
        
        # Extract improvement percentage
        estimated_improvement = 0.0
        for line in content.split("\n"):
            if "ESTIMATED_IMPROVEMENT" in line or "estimated improvement" in line.lower():
                try:
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)%', line)
                    if match:
                        estimated_improvement = float(match.group(1))
                except:
                    pass
        
        # Extract confidence
        confidence = 0.5
        for line in content.split("\n"):
            if "CONFIDENCE" in line or "confidence" in line.lower():
                try:
                    import re
                    match = re.search(r'0?\.\d+', line)
                    if match:
                        confidence = float(match.group(0))
                except:
                    pass
        
        # Extract recommendation
        recommendation = ""
        if "RECOMMENDATION:" in content:
            recommendation = content.split("RECOMMENDATION:")[-1].strip()
        elif "recommendation:" in content.lower():
            recommendation = content.split("recommendation:")[-1].strip()
        else:
            recommendation = content[:200]
        
        return {
            "should_trigger": should_trigger,
            "estimated_improvement": estimated_improvement,
            "confidence": confidence,
            "recommendation": recommendation
        }
    
    def _infer_task_type_from_model(self, model_key: str) -> str:
        """Infer task type from model key."""
        if "coder" in model_key.lower():
            return "code_generation"
        elif "r1" in model_key.lower() or "reasoning" in model_key.lower():
            return "reasoning"
        else:
            return "general"
    
    def _execute_trigger(self, trigger: FineTuningTrigger):
        """Execute fine-tuning trigger."""
        logger.info(f"[AUTO-FINE-TUNE] Executing trigger: {trigger.trigger_id} for {trigger.task_type}")
        
        if not self.fine_tuning or not self.repo_access:
            logger.warning("[AUTO-FINE-TUNE] Fine-tuning system or repo access not available")
            return
        
        try:
            # Prepare dataset
            dataset = self.fine_tuning.prepare_dataset(
                task_type=trigger.task_type,
                dataset_name=f"auto_{trigger.task_type}_{datetime.now().strftime('%Y%m%d')}",
                min_trust_score=self.min_trust,
                num_examples=trigger.dataset_size if trigger.dataset_size > 0 else self.min_examples
            )
            
            # Request approval (or auto-approve if enabled)
            base_model = self._select_base_model(trigger.task_type)
            approval_request = self.fine_tuning.request_fine_tuning_approval(
                dataset=dataset,
                base_model=base_model,
                target_model_name=f"grace-{trigger.task_type}-auto-{datetime.now().strftime('%Y%m%d')}",
                method=FineTuningMethod.QLORA
            )
            
            if self.auto_approve:
                logger.warning("[AUTO-FINE-TUNE] AUTO-APPROVING fine-tuning (use with caution!)")
                # Auto-approve and start
                self.fine_tuning.approve_and_start_fine_tuning(
                    job_id=approval_request.job_id,
                    user_id="GU-grace-autonomous",
                    dry_run=False  # Actually train!
                )
            else:
                logger.info(f"[AUTO-FINE-TUNE] Fine-tuning approval requested: {approval_request.job_id}")
                logger.info(f"[AUTO-FINE-TUNE] Recommendation: {approval_request.recommendation}")
                logger.info(f"[AUTO-FINE-TUNE] To approve: POST /llm/fine-tune/approve/{approval_request.job_id}")
        
        except Exception as e:
            logger.error(f"[AUTO-FINE-TUNE] Error executing trigger: {e}")
    
    def _select_base_model(self, task_type: str) -> str:
        """Select base model for fine-tuning based on task type."""
        if "code" in task_type.lower():
            return "qwen2.5-coder:7b-instruct"  # Smaller model for efficiency
        elif "reasoning" in task_type.lower():
            return "qwen2.5:7b-instruct"
        else:
            return "qwen2.5:7b-instruct"
    
    def get_trigger_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get trigger history."""
        return [
            {
                "trigger_id": t.trigger_id,
                "reason": t.reason.value,
                "task_type": t.task_type,
                "dataset_size": t.dataset_size,
                "avg_trust_score": t.avg_trust_score,
                "estimated_improvement": t.estimated_improvement,
                "confidence": t.confidence,
                "should_trigger": t.should_trigger,
                "recommendation": t.recommendation,
                "timestamp": t.timestamp.isoformat()
            }
            for t in self.trigger_history[-limit:]
        ]


# Global instance
_autonomous_trigger: Optional[AutonomousFineTuningTrigger] = None


def get_autonomous_fine_tuning_trigger(
    multi_llm_client: Optional[MultiLLMClient] = None,
    fine_tuning_system: Optional[LLMFineTuningSystem] = None,
    repo_access: Optional[RepositoryAccessLayer] = None,
    learning_integration: Optional[LearningIntegration] = None,
    auto_approve: bool = False
) -> AutonomousFineTuningTrigger:
    """Get or create global autonomous fine-tuning trigger instance."""
    global _autonomous_trigger
    if _autonomous_trigger is None:
        _autonomous_trigger = AutonomousFineTuningTrigger(
            multi_llm_client=multi_llm_client,
            fine_tuning_system=fine_tuning_system,
            repo_access=repo_access,
            learning_integration=learning_integration,
            auto_approve=auto_approve
        )
    return _autonomous_trigger
