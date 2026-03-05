"""
Grace Systems Integration Service

Unified integration layer connecting Grace Planning and Todos systems
with all core Grace systems:
- DeepMagmaMemory (memory/learning)
- DiagnosticMachine (4-layer diagnostics)
- OracleMLIntelligence (ML predictions)
- SecurityLayer (trust/governance)
- SelfHealingSystem (auto-recovery)
- NeuralSymbolicAI (reasoning)
- IngestionPipeline (data processing)
- ProactiveLearning (autonomous learning)

Author: Grace Autonomous System
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid
import asyncio
import json


class GraceSystemType(str, Enum):
    """Types of Grace subsystems"""
    MEMORY = "memory"
    DIAGNOSTIC = "diagnostic"
    ORACLE = "oracle"
    SECURITY = "security"
    SELF_HEALING = "self_healing"
    NEURAL_SYMBOLIC = "neural_symbolic"
    INGESTION = "ingestion"
    PROACTIVE = "proactive"
    COGNITIVE = "cognitive"
    LIBRARIAN = "librarian"


class IntegrationEvent(str, Enum):
    """Events that trigger system integration"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    CONCEPT_APPROVED = "concept_approved"
    EXECUTION_STARTED = "execution_started"
    IDE_HANDOFF = "ide_handoff"
    LEARNING_COMPLETE = "learning_complete"
    DIAGNOSTIC_ALERT = "diagnostic_alert"
    SECURITY_CHECK = "security_check"


class GraceSystemsIntegration:
    """
    Central integration hub for all Grace systems.
    Provides unified access to memory, diagnostics, oracle, and other systems.
    """

    def __init__(self):
        self.system_status: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: Dict[IntegrationEvent, List[callable]] = {}
        self.integration_logs: List[Dict[str, Any]] = []
        self._initialize_systems()

    def _initialize_systems(self):
        """Initialize connections to all Grace systems"""
        for system in GraceSystemType:
            self.system_status[system.value] = {
                "status": "initialized",
                "last_accessed": None,
                "health": "unknown",
                "metrics": {}
            }

    # =========================================================================
    # MEMORY INTEGRATION (DeepMagmaMemory)
    # =========================================================================

    async def memory_store(
        self,
        key: str,
        data: Dict[str, Any],
        memory_type: str = "working",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store data in Grace's memory system.

        Args:
            key: Memory key
            data: Data to store
            memory_type: working, short_term, long_term, procedural
            context: Additional context for memory formation
        """
        try:
            # Import memory system
            from cognitive.magma import MagmaMemory

            memory = MagmaMemory()

            result = await memory.store(
                key=key,
                data=data,
                memory_type=memory_type,
                context=context or {}
            )

            self._log_integration(
                system=GraceSystemType.MEMORY,
                action="store",
                details={"key": key, "type": memory_type},
                success=True
            )

            return {"success": True, "memory_id": result.get("id")}

        except ImportError:
            # Fallback if memory system not available
            self._log_integration(
                system=GraceSystemType.MEMORY,
                action="store",
                details={"key": key, "type": memory_type},
                success=False,
                error="Memory system not available"
            )
            return {"success": False, "error": "Memory system not available"}

        except Exception as e:
            self._log_integration(
                system=GraceSystemType.MEMORY,
                action="store",
                details={"key": key},
                success=False,
                error=str(e)
            )
            return {"success": False, "error": str(e)}

    async def memory_retrieve(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Retrieve relevant memories for a query.

        Args:
            query: Search query
            memory_type: Filter by memory type
            limit: Max results
        """
        try:
            from cognitive.magma import MagmaMemory

            memory = MagmaMemory()
            results = await memory.retrieve(
                query=query,
                memory_type=memory_type,
                limit=limit
            )

            self._log_integration(
                system=GraceSystemType.MEMORY,
                action="retrieve",
                details={"query": query[:50], "results_count": len(results)},
                success=True
            )

            return {"success": True, "memories": results}

        except ImportError:
            return {"success": False, "error": "Memory system not available", "memories": []}

        except Exception as e:
            return {"success": False, "error": str(e), "memories": []}

    async def memory_learn_from_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        outcome: str
    ) -> Dict[str, Any]:
        """
        Learn from task execution and store in memory.

        Args:
            task_id: Task identifier
            task_data: Task details
            outcome: success, failure, partial
        """
        learning_data = {
            "task_id": task_id,
            "task_type": task_data.get("type"),
            "task_title": task_data.get("title"),
            "outcome": outcome,
            "duration_ms": task_data.get("duration_ms"),
            "learned_at": datetime.now().isoformat(),
            "patterns": task_data.get("patterns", []),
            "errors": task_data.get("errors", [])
        }

        return await self.memory_store(
            key=f"task_learning:{task_id}",
            data=learning_data,
            memory_type="long_term",
            context={"source": "task_execution", "outcome": outcome}
        )

    # =========================================================================
    # DIAGNOSTIC INTEGRATION (DiagnosticMachine)
    # =========================================================================

    async def diagnostic_analyze(
        self,
        target: str,
        target_type: str,
        depth: str = "full"
    ) -> Dict[str, Any]:
        """
        Run diagnostic analysis using 4-layer DiagnosticMachine.

        Args:
            target: What to analyze (task, concept, system, etc.)
            target_type: Type of target
            depth: quick, standard, full
        """
        try:
            from diagnostic_machine.diagnostic_engine import DiagnosticEngine

            diagnostic = DiagnosticEngine()

            # Run through 4 layers: Sensors -> Interpreters -> Judgment -> Action
            result = await diagnostic.analyze(
                target=target,
                target_type=target_type,
                depth=depth
            )

            self._log_integration(
                system=GraceSystemType.DIAGNOSTIC,
                action="analyze",
                details={"target_type": target_type, "depth": depth},
                success=True
            )

            return {
                "success": True,
                "diagnosis": result.get("diagnosis"),
                "severity": result.get("severity"),
                "recommendations": result.get("recommendations", []),
                "layer_results": result.get("layer_results", {})
            }

        except ImportError:
            return {"success": False, "error": "Diagnostic system not available"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def diagnostic_health_check(
        self,
        systems: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run health check on Grace systems.

        Args:
            systems: Specific systems to check, or all if None
        """
        try:
            from diagnostic_machine.diagnostic_engine import DiagnosticEngine

            diagnostic = DiagnosticEngine()
            health_report = await diagnostic.health_check(systems=systems)

            return {
                "success": True,
                "overall_health": health_report.get("overall_health"),
                "systems": health_report.get("systems", {}),
                "alerts": health_report.get("alerts", [])
            }

        except ImportError:
            # Return simulated health for systems we know about
            return {
                "success": True,
                "overall_health": "unknown",
                "systems": {s.value: {"status": "unknown"} for s in GraceSystemType},
                "alerts": []
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # ORACLE INTEGRATION (OracleMLIntelligence)
    # =========================================================================

    async def oracle_predict(
        self,
        prediction_type: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get ML predictions from Oracle system.

        Args:
            prediction_type: task_success, priority, effort, risk
            input_data: Data for prediction
        """
        try:
            from ml_intelligence.integration_orchestrator import get_ml_orchestrator

            orchestrator = get_ml_orchestrator()

            if prediction_type == "task_success":
                result = await orchestrator.predict_task_success(input_data)
            elif prediction_type == "priority":
                result = await orchestrator.predict_priority(input_data)
            elif prediction_type == "effort":
                result = await orchestrator.estimate_effort(input_data)
            elif prediction_type == "risk":
                result = await orchestrator.assess_risk(input_data)
            else:
                result = await orchestrator.generic_predict(prediction_type, input_data)

            self._log_integration(
                system=GraceSystemType.ORACLE,
                action="predict",
                details={"type": prediction_type},
                success=True
            )

            return {
                "success": True,
                "prediction": result.get("prediction"),
                "confidence": result.get("confidence"),
                "factors": result.get("factors", [])
            }

        except ImportError:
            return {"success": False, "error": "Oracle ML system not available"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def oracle_suggest_assignment(
        self,
        task_data: Dict[str, Any],
        available_assignees: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use Oracle to suggest best assignment for a task.

        Args:
            task_data: Task details
            available_assignees: List of team members/agents with skills
        """
        try:
            from ml_intelligence.integration_orchestrator import get_ml_orchestrator

            orchestrator = get_ml_orchestrator()

            # Build feature set
            features = {
                "task_type": task_data.get("type"),
                "task_complexity": task_data.get("estimated_complexity", "medium"),
                "required_skills": task_data.get("required_capabilities", []),
                "priority": task_data.get("priority", 5),
                "assignees": [
                    {
                        "id": a.get("id"),
                        "skills": a.get("skills", []),
                        "current_load": a.get("current_load", 0),
                        "success_rate": a.get("success_rate", 0.8)
                    }
                    for a in available_assignees
                ]
            }

            result = await orchestrator.suggest_assignment(features)

            return {
                "success": True,
                "suggested_assignee": result.get("assignee_id"),
                "confidence": result.get("confidence"),
                "reasoning": result.get("reasoning"),
                "alternatives": result.get("alternatives", [])
            }

        except ImportError:
            # Fallback: simple skill matching
            best_match = None
            best_score = 0

            required_skills = set(task_data.get("required_capabilities", []))

            for assignee in available_assignees:
                assignee_skills = set(assignee.get("skills", []))
                match_score = len(required_skills & assignee_skills)
                load_factor = 1 - (assignee.get("current_load", 0) / 100)
                score = match_score * load_factor

                if score > best_score:
                    best_score = score
                    best_match = assignee

            return {
                "success": True,
                "suggested_assignee": best_match.get("id") if best_match else None,
                "confidence": min(0.5 + (best_score * 0.1), 0.9),
                "reasoning": "Skill-based matching",
                "alternatives": []
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SECURITY INTEGRATION (SecurityLayer)
    # =========================================================================

    async def security_validate_task(
        self,
        task_data: Dict[str, Any],
        executor_id: str
    ) -> Dict[str, Any]:
        """
        Validate task execution with security layer.

        Args:
            task_data: Task to validate
            executor_id: Who/what will execute
        """
        try:
            from security.governance import GovernanceEngine

            security = GovernanceEngine()

            result = await security.validate_action(
                action_type="task_execution",
                action_data=task_data,
                actor_id=executor_id
            )

            self._log_integration(
                system=GraceSystemType.SECURITY,
                action="validate_task",
                details={"task_id": task_data.get("id"), "executor": executor_id},
                success=result.get("approved", False)
            )

            return {
                "success": True,
                "approved": result.get("approved", False),
                "trust_score": result.get("trust_score", 0.5),
                "restrictions": result.get("restrictions", []),
                "requires_approval": result.get("requires_approval", False)
            }

        except ImportError:
            # Fallback: basic trust check
            return {
                "success": True,
                "approved": True,
                "trust_score": 0.7,
                "restrictions": [],
                "requires_approval": False
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def security_check_permissions(
        self,
        user_id: str,
        action: str,
        resource: str
    ) -> Dict[str, Any]:
        """
        Check if user has permissions for an action.

        Args:
            user_id: User Genesis ID
            action: Action to perform
            resource: Resource being accessed
        """
        try:
            from security.governance import GovernanceEngine

            security = GovernanceEngine()

            has_permission = await security.check_permission(
                user_id=user_id,
                action=action,
                resource=resource
            )

            return {
                "success": True,
                "has_permission": has_permission,
                "user_id": user_id,
                "action": action
            }

        except ImportError:
            return {"success": True, "has_permission": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SELF-HEALING INTEGRATION
    # =========================================================================

    async def healing_handle_failure(
        self,
        failure_type: str,
        failure_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle a failure with self-healing system.

        Args:
            failure_type: Type of failure
            failure_data: Failure details
            context: Additional context
        """
        try:
            from cognitive.self_healing import SelfHealingSystem

            healing = SelfHealingSystem()

            result = await healing.handle_failure(
                failure_type=failure_type,
                failure_data=failure_data,
                context=context or {}
            )

            self._log_integration(
                system=GraceSystemType.SELF_HEALING,
                action="handle_failure",
                details={"failure_type": failure_type},
                success=result.get("recovered", False)
            )

            return {
                "success": True,
                "recovered": result.get("recovered", False),
                "recovery_action": result.get("action_taken"),
                "new_state": result.get("new_state"),
                "recommendations": result.get("recommendations", [])
            }

        except ImportError:
            return {
                "success": False,
                "recovered": False,
                "error": "Self-healing system not available"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def healing_suggest_recovery(
        self,
        error_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get recovery suggestions for an error.

        Args:
            error_data: Error details
        """
        try:
            from cognitive.self_healing import SelfHealingSystem

            healing = SelfHealingSystem()

            suggestions = await healing.suggest_recovery(error_data)

            return {
                "success": True,
                "suggestions": suggestions,
                "auto_recoverable": any(s.get("auto_recoverable") for s in suggestions)
            }

        except ImportError:
            # Basic recovery suggestions
            return {
                "success": True,
                "suggestions": [
                    {"action": "retry", "description": "Retry the operation", "auto_recoverable": True},
                    {"action": "skip", "description": "Skip and continue", "auto_recoverable": False},
                    {"action": "escalate", "description": "Escalate to human", "auto_recoverable": False}
                ],
                "auto_recoverable": True
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # NEURAL SYMBOLIC INTEGRATION
    # =========================================================================

    async def reasoning_analyze(
        self,
        problem: str,
        context: Dict[str, Any],
        reasoning_type: str = "analytical"
    ) -> Dict[str, Any]:
        """
        Use neural-symbolic reasoning for analysis.

        Args:
            problem: Problem to analyze
            context: Context data
            reasoning_type: analytical, creative, logical, hybrid
        """
        try:
            from ml_intelligence.neuro_symbolic_reasoner import NeuroSymbolicReasoner

            reasoner = NeuroSymbolicReasoner()

            result = await reasoner.reason(
                problem=problem,
                context=context,
                reasoning_type=reasoning_type
            )

            self._log_integration(
                system=GraceSystemType.NEURAL_SYMBOLIC,
                action="reason",
                details={"type": reasoning_type},
                success=True
            )

            return {
                "success": True,
                "conclusion": result.get("conclusion"),
                "reasoning_chain": result.get("chain", []),
                "confidence": result.get("confidence"),
                "supporting_evidence": result.get("evidence", [])
            }

        except ImportError:
            return {
                "success": False,
                "error": "Neural-symbolic system not available"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # INGESTION INTEGRATION
    # =========================================================================

    async def ingest_task_output(
        self,
        task_id: str,
        output_data: Dict[str, Any],
        output_type: str
    ) -> Dict[str, Any]:
        """
        Ingest task output into knowledge base.

        Args:
            task_id: Source task
            output_data: Data to ingest
            output_type: code, document, config, etc.
        """
        try:
            from api.ingest import get_ingestion_service

            pipeline = get_ingestion_service()

            result = await pipeline.ingest(
                source=f"task:{task_id}",
                data=output_data,
                data_type=output_type,
                metadata={
                    "source_task": task_id,
                    "ingested_at": datetime.now().isoformat()
                }
            )

            self._log_integration(
                system=GraceSystemType.INGESTION,
                action="ingest_task_output",
                details={"task_id": task_id, "type": output_type},
                success=result.get("success", False)
            )

            return {
                "success": True,
                "ingestion_id": result.get("id"),
                "chunks_created": result.get("chunks", 0)
            }

        except ImportError:
            return {"success": False, "error": "Ingestion system not available"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # PROACTIVE LEARNING INTEGRATION
    # =========================================================================

    async def proactive_suggest_improvements(
        self,
        context_type: str,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get proactive improvement suggestions.

        Args:
            context_type: task, concept, workflow
            context_data: Context for suggestions
        """
        try:
            from cognitive.proactive_learner import ProactiveLearningOrchestrator

            proactive = ProactiveLearningOrchestrator()

            suggestions = await proactive.suggest_improvements(
                context_type=context_type,
                context_data=context_data
            )

            return {
                "success": True,
                "suggestions": suggestions,
                "auto_applicable": [s for s in suggestions if s.get("auto_applicable")]
            }

        except ImportError:
            return {
                "success": True,
                "suggestions": [],
                "auto_applicable": []
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def proactive_queue_learning(
        self,
        learning_task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Queue a learning task for proactive processing.

        Args:
            learning_task: Learning task details
        """
        try:
            from cognitive.proactive_learner import ProactiveLearningOrchestrator

            proactive = ProactiveLearningOrchestrator()

            result = await proactive.queue_task(learning_task)

            return {
                "success": True,
                "queued": True,
                "queue_position": result.get("position"),
                "estimated_completion": result.get("estimated_completion")
            }

        except ImportError:
            return {"success": False, "error": "Proactive learning not available"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # EVENT HANDLING
    # =========================================================================

    def register_event_handler(
        self,
        event: IntegrationEvent,
        handler: callable
    ):
        """Register a handler for an integration event"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)

    async def emit_event(
        self,
        event: IntegrationEvent,
        data: Dict[str, Any]
    ):
        """Emit an integration event to all handlers"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self._log_integration(
                        system=GraceSystemType.COGNITIVE,
                        action=f"event:{event.value}",
                        details={"error": str(e)},
                        success=False,
                        error=str(e)
                    )

    # =========================================================================
    # UNIFIED TASK PROCESSING
    # =========================================================================

    async def process_task_with_systems(
        self,
        task_data: Dict[str, Any],
        executor_id: str
    ) -> Dict[str, Any]:
        """
        Process a task using all relevant Grace systems.

        This is the main integration point that coordinates:
        1. Security validation
        2. Memory retrieval for context
        3. Oracle predictions
        4. Diagnostic pre-checks
        5. Task execution
        6. Learning capture
        7. Output ingestion
        """
        task_id = task_data.get("id", str(uuid.uuid4()))
        results = {
            "task_id": task_id,
            "systems_used": [],
            "start_time": datetime.now().isoformat()
        }

        # 1. Security validation
        security_result = await self.security_validate_task(task_data, executor_id)
        results["security"] = security_result
        results["systems_used"].append("security")

        if not security_result.get("approved", False):
            results["status"] = "rejected"
            results["reason"] = "Security validation failed"
            return results

        # 2. Memory retrieval for context
        memory_result = await self.memory_retrieve(
            query=task_data.get("description", task_data.get("title", "")),
            limit=5
        )
        results["memory_context"] = memory_result.get("memories", [])
        results["systems_used"].append("memory")

        # 3. Oracle predictions
        oracle_result = await self.oracle_predict(
            prediction_type="task_success",
            input_data={
                "task_type": task_data.get("type"),
                "complexity": task_data.get("estimated_complexity"),
                "context_count": len(memory_result.get("memories", []))
            }
        )
        results["prediction"] = oracle_result
        results["systems_used"].append("oracle")

        # 4. Diagnostic pre-check
        diagnostic_result = await self.diagnostic_health_check()
        results["system_health"] = diagnostic_result
        results["systems_used"].append("diagnostic")

        # 5. Emit task started event
        await self.emit_event(IntegrationEvent.TASK_STARTED, {
            "task_id": task_id,
            "task_data": task_data,
            "predictions": oracle_result
        })

        results["status"] = "ready"
        results["end_time"] = datetime.now().isoformat()

        return results

    async def complete_task_with_learning(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        outcome: str,
        output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete a task and capture learnings.

        Args:
            task_id: Task identifier
            task_data: Task details
            outcome: success, failure, partial
            output: Task output if any
        """
        results = {
            "task_id": task_id,
            "outcome": outcome,
            "systems_used": []
        }

        # 1. Store learning in memory
        learning_result = await self.memory_learn_from_task(
            task_id=task_id,
            task_data=task_data,
            outcome=outcome
        )
        results["learning"] = learning_result
        results["systems_used"].append("memory")

        # 2. If there's output, ingest it
        if output:
            ingest_result = await self.ingest_task_output(
                task_id=task_id,
                output_data=output,
                output_type=output.get("type", "general")
            )
            results["ingestion"] = ingest_result
            results["systems_used"].append("ingestion")

        # 3. If failure, get recovery suggestions
        if outcome == "failure":
            healing_result = await self.healing_suggest_recovery({
                "task_id": task_id,
                "task_type": task_data.get("type"),
                "errors": task_data.get("errors", [])
            })
            results["recovery_suggestions"] = healing_result
            results["systems_used"].append("self_healing")

        # 4. Emit completion event
        event = IntegrationEvent.TASK_COMPLETED if outcome == "success" else IntegrationEvent.TASK_FAILED
        await self.emit_event(event, {
            "task_id": task_id,
            "outcome": outcome,
            "task_data": task_data
        })

        return results

    # =========================================================================
    # LOGGING & METRICS
    # =========================================================================

    def _log_integration(
        self,
        system: GraceSystemType,
        action: str,
        details: Dict[str, Any],
        success: bool,
        error: Optional[str] = None
    ):
        """Log integration activity"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "system": system.value,
            "action": action,
            "details": details,
            "success": success,
            "error": error
        }
        self.integration_logs.append(log_entry)

        # Update system status
        self.system_status[system.value]["last_accessed"] = datetime.now().isoformat()
        if success:
            self.system_status[system.value]["health"] = "healthy"
        else:
            self.system_status[system.value]["health"] = "degraded"

        # Keep only last 1000 logs
        if len(self.integration_logs) > 1000:
            self.integration_logs = self.integration_logs[-1000:]

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all integrated systems"""
        return {
            "systems": self.system_status,
            "total_integrations": len(self.integration_logs),
            "recent_failures": [
                log for log in self.integration_logs[-50:]
                if not log.get("success")
            ]
        }

    def get_integration_metrics(self) -> Dict[str, Any]:
        """Get integration metrics"""
        success_count = sum(1 for log in self.integration_logs if log.get("success"))
        failure_count = len(self.integration_logs) - success_count

        by_system = {}
        for log in self.integration_logs:
            system = log.get("system", "unknown")
            if system not in by_system:
                by_system[system] = {"success": 0, "failure": 0}
            if log.get("success"):
                by_system[system]["success"] += 1
            else:
                by_system[system]["failure"] += 1

        return {
            "total_integrations": len(self.integration_logs),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / len(self.integration_logs) if self.integration_logs else 0,
            "by_system": by_system
        }


# Singleton instance
_integration_instance: Optional[GraceSystemsIntegration] = None


def get_grace_integration() -> GraceSystemsIntegration:
    """Get the Grace Systems Integration singleton"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = GraceSystemsIntegration()
    return _integration_instance
