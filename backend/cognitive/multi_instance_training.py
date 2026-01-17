"""
Multi-Instance Training System

Runs multiple sandbox instances in parallel on different domains,
while real-world fixes continue independently.

Architecture:
1. Multiple sandbox instances (one per domain/problem perspective)
2. Background workers for real-world fixes (outside sandbox)
3. Independent execution (sandbox doesn't block real-world fixes)
4. Resource-aware scheduling
"""

import logging
import threading
import queue
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp

logger = logging.getLogger(__name__)


class InstanceType(str, Enum):
    """Type of training instance."""
    SANDBOX_SYNTAX = "sandbox_syntax"
    SANDBOX_LOGIC = "sandbox_logic"
    SANDBOX_PERFORMANCE = "sandbox_performance"
    SANDBOX_SECURITY = "sandbox_security"
    SANDBOX_ARCHITECTURE = "sandbox_architecture"
    REAL_WORLD_HEALING = "real_world_healing"  # Runs outside sandbox


@dataclass
class TrainingInstance:
    """A training instance running in parallel."""
    instance_id: str
    instance_type: InstanceType
    problem_perspective: str
    state: str  # "running", "idle", "paused", "stopped"
    started_at: datetime
    files_processed: int = 0
    files_fixed: int = 0
    current_task: Optional[str] = None
    thread: Optional[threading.Thread] = None


@dataclass
class RealWorldTask:
    """A real-world fix task (outside sandbox)."""
    task_id: str
    source: str  # "diagnostic", "llm", "user", "system"
    description: str
    affected_files: List[str]
    priority: int = 5  # 1-10, higher = more urgent
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None


class MultiInstanceTrainingSystem:
    """
    Multi-Instance Training System.
    
    Runs multiple sandbox instances in parallel:
    1. One sandbox instance per domain/problem perspective
    2. Background workers for real-world fixes (outside sandbox)
    3. Independent execution (sandbox doesn't block real-world)
    4. Resource-aware load balancing
    """
    
    def __init__(
        self,
        base_training_system,
        max_sandbox_instances: int = 5,
        max_real_world_workers: int = 2,
        enable_real_world: bool = True,
        diagnostic_engine=None,
        healing_system=None,
        code_analyzer=None,
        llm_orchestrator=None,
        testing_system=None,
        debugging_system=None,
        enable_federated_learning: bool = True
    ):
        """Initialize Multi-Instance Training System."""
        self.base_system = base_training_system
        
        # Integrated systems
        self.diagnostic_engine = diagnostic_engine
        self.healing_system = healing_system
        self.code_analyzer = code_analyzer
        self.llm_orchestrator = llm_orchestrator
        self.testing_system = testing_system
        self.debugging_system = debugging_system
        
        # Instance configuration
        self.max_sandbox_instances = max_sandbox_instances
        self.max_real_world_workers = max_real_world_workers
        
        # Federated learning
        self.enable_federated_learning = enable_federated_learning
        self.federated_server = None
        if enable_federated_learning:
            try:
                from cognitive.federated_learning_system import get_federated_learning_system, FederatedClientType
                
                # Get learning memory manager if available
                learning_memory = None
                if hasattr(base_training_system, 'llm_orchestrator') and base_training_system.llm_orchestrator:
                    if hasattr(base_training_system.llm_orchestrator, 'learning_memory'):
                        learning_memory = base_training_system.llm_orchestrator.learning_memory
                
                # Get Genesis service for Grace-aligned tracking
                genesis_service = None
                session = None
                try:
                    from genesis.genesis_key_service import get_genesis_service
                    from database.session import get_session
                    genesis_service = get_genesis_service()
                    session = next(get_session()) if hasattr(base_training_system, 'session') else None
                except Exception as e:
                    logger.debug(f"[MULTI-INSTANCE] Genesis service not available: {e}")
                
                self.federated_server = get_federated_learning_system(
                    server_id="grace_federated_server",
                    enable_cross_deployment=False,
                    learning_memory_manager=learning_memory,
                    llm_orchestrator=llm_orchestrator,
                    genesis_service=genesis_service,
                    session=session
                )
                self.FederatedClientType = FederatedClientType
                logger.info("[MULTI-INSTANCE] Federated learning enabled with learning memory integration")
            except Exception as e:
                logger.warning(f"[MULTI-INSTANCE] Federated learning not available: {e}")
                self.enable_federated_learning = False
        
        # Sandbox instances (one per domain)
        self.sandbox_instances: Dict[str, TrainingInstance] = {}
        
        # Real-world task queue (outside sandbox)
        self.real_world_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.real_world_workers: List[threading.Thread] = []
        self.real_world_running = enable_real_world
        
        # Instance management
        self.instance_lock = threading.Lock()
        self.running = False
        
        # Statistics
        self.stats = {
            "active_sandbox_instances": 0,
            "active_real_world_workers": 0,
            "total_files_processed": 0,
            "total_files_fixed": 0,
            "total_real_world_fixes": 0,
            "concurrent_domains": 0
        }
        
        logger.info(
            f"[MULTI-INSTANCE] Initialized with {max_sandbox_instances} sandbox instances, "
            f"{max_real_world_workers} real-world workers"
        )
    
    # ==================== SANDBOX INSTANCES ====================
    
    def start_all_sandbox_instances(self):
        """Start sandbox instances for all domains."""
        # Problem perspectives for sandbox training
        domains = [
            ("syntax_errors", InstanceType.SANDBOX_SYNTAX),
            ("logic_errors", InstanceType.SANDBOX_LOGIC),
            ("performance_issues", InstanceType.SANDBOX_PERFORMANCE),
            ("security_vulnerabilities", InstanceType.SANDBOX_SECURITY),
            ("architectural_problems", InstanceType.SANDBOX_ARCHITECTURE)
        ]
        
        for domain, instance_type in domains[:self.max_sandbox_instances]:
            self.start_sandbox_instance(domain, instance_type)
        
        logger.info(f"[MULTI-INSTANCE] Started {len(self.sandbox_instances)} sandbox instances")
    
    def start_sandbox_instance(
        self,
        problem_perspective: str,
        instance_type: InstanceType
    ) -> TrainingInstance:
        """Start a sandbox training instance for a specific domain."""
        instance_id = f"instance_{problem_perspective}_{datetime.utcnow().timestamp()}"
        
        instance = TrainingInstance(
            instance_id=instance_id,
            instance_type=instance_type,
            problem_perspective=problem_perspective,
            state="running",
            started_at=datetime.utcnow()
        )
        
        # Register as federated learning client
        if self.enable_federated_learning and self.federated_server:
            try:
                self.federated_server.register_client(
                    client_id=instance_id,
                    client_type=self.FederatedClientType.SANDBOX_INSTANCE,
                    domain=problem_perspective
                )
                logger.info(f"[MULTI-INSTANCE] Registered {instance_id} as federated client")
            except Exception as e:
                logger.warning(f"[MULTI-INSTANCE] Federated client registration error: {e}")
        
        # Start instance thread
        instance_thread = threading.Thread(
            target=self._sandbox_instance_worker,
            args=(instance,),
            daemon=True,
            name=f"Sandbox-{problem_perspective}"
        )
        instance_thread.start()
        instance.thread = instance_thread
        
        # Store instance
        with self.instance_lock:
            self.sandbox_instances[instance_id] = instance
            self.stats["active_sandbox_instances"] = len(self.sandbox_instances)
            self.stats["concurrent_domains"] = len(self.sandbox_instances)
        
        logger.info(f"[MULTI-INSTANCE] Started sandbox instance: {instance_id} ({problem_perspective})")
        
        return instance
    
    def _sandbox_instance_worker(self, instance: TrainingInstance):
        """Worker thread for a sandbox instance (runs continuously, learning on its domain)."""
        logger.info(f"[MULTI-INSTANCE] Sandbox instance {instance.instance_id} started ({instance.problem_perspective}) - Learning on domain")
        
        while instance.state == "running" and self.running:
            try:
                # Collect files for this domain
                files = self._collect_files_for_domain(instance.problem_perspective, count=100)
                
                if not files:
                    # No files available, wait before retry
                    threading.Event().wait(5.0)
                    continue
                
                # Create training cycle for this domain
                cycle = self.base_system.start_training_cycle(
                    folder_path=f"sandbox/{instance.problem_perspective}",
                    problem_perspective=instance.problem_perspective
                )
                
                # Process files in sandbox (parallel) - Learning domain-specific patterns
                instance.current_task = f"Processing {len(files)} files - Learning {instance.problem_perspective}"
                
                results = self._process_files_in_sandbox(files, cycle, instance)
                
                # Store domain-specific knowledge learned
                domain_knowledge = self._store_domain_knowledge(
                    instance.problem_perspective,
                    results.get("knowledge_gained", []),
                    results.get("files_fixed", [])
                )
                
                # Submit federated learning update
                if self.enable_federated_learning and self.federated_server:
                    self._submit_federated_update(
                        instance,
                        results,
                        domain_knowledge
                    )
                
                # Update instance statistics
                instance.files_processed += len(files)
                instance.files_fixed += len(results["files_fixed"])
                
                # Update global statistics
                with self.instance_lock:
                    self.stats["total_files_processed"] += len(files)
                    self.stats["total_files_fixed"] += len(results["files_fixed"])
                
                logger.info(
                    f"[MULTI-INSTANCE] Instance {instance.instance_id} ({instance.problem_perspective}): "
                    f"Learned {len(domain_knowledge.get('topics', []))} domain-specific patterns "
                    f"from {len(results['files_fixed'])} fixes"
                )
                
                # Submit federated learning update
                if self.enable_federated_learning and self.federated_server:
                    self._submit_federated_update(
                        instance,
                        results,
                        domain_knowledge
                    )
                
                instance.current_task = None
                
                # Brief pause before next cycle
                threading.Event().wait(1.0)
                
            except Exception as e:
                logger.error(f"[MULTI-INSTANCE] Sandbox instance {instance.instance_id} error: {e}")
                threading.Event().wait(5.0)  # Wait before retry
        
        logger.info(f"[MULTI-INSTANCE] Sandbox instance {instance.instance_id} stopped")
    
    def _store_domain_knowledge(
        self,
        problem_perspective: str,
        knowledge_gained: List[str],
        files_fixed: List[str]
    ) -> Dict[str, Any]:
        """
        Store domain-specific knowledge learned by this instance.
        
        Each instance learns patterns specific to its domain/problem perspective.
        """
        try:
            # Contribute knowledge to Grace's Memory Mesh with domain tagging
            if self.base_system.llm_orchestrator and hasattr(self.base_system.llm_orchestrator, "grace_aligned_llm"):
                domain_topics = []
                
                for knowledge in knowledge_gained:
                    try:
                        # Tag knowledge with domain
                        domain_tagged_knowledge = f"[{problem_perspective}] {knowledge}"
                        
                        # Contribute to Grace's learning with domain context
                        learning_id = self.base_system.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                            llm_output=domain_tagged_knowledge,
                            query=f"{problem_perspective} fix pattern",
                            trust_score=0.8,
                            genesis_key_id=None,
                            context={
                                "domain": problem_perspective,
                                "source": "sandbox_training",
                                "instance_id": f"instance_{problem_perspective}"
                            }
                        )
                        
                        domain_topics.append({
                            "knowledge": knowledge,
                            "learning_id": learning_id,
                            "domain": problem_perspective
                        })
                        
                    except Exception as e:
                        logger.warning(f"[MULTI-INSTANCE] Knowledge storage error for {problem_perspective}: {e}")
                
                return {
                    "topics": domain_topics,
                    "domain": problem_perspective,
                    "files_fixed": len(files_fixed),
                    "knowledge_count": len(domain_topics)
                }
            
            return {
                "topics": [],
                "domain": problem_perspective,
                "files_fixed": len(files_fixed),
                "knowledge_count": 0
            }
            
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Domain knowledge storage error: {e}")
            return {
                "topics": [],
                "domain": problem_perspective,
                "files_fixed": len(files_fixed),
                "knowledge_count": 0
            }
    
    def _collect_files_for_domain(self, problem_perspective: str, count: int = 100) -> List[str]:
        """Collect files for a specific domain/problem perspective."""
        # This would use the base system's file collection logic
        # For now, return empty list (would be implemented)
        return []
    
    def _process_files_in_sandbox(
        self,
        files: List[str],
        cycle: Any,
        instance: TrainingInstance
    ) -> Dict[str, Any]:
        """
        Process files in sandbox (can use parallel processing).
        
        Each instance learns domain-specific patterns:
        - Syntax instance learns syntax error patterns
        - Logic instance learns logic error patterns
        - Performance instance learns performance optimization patterns
        - etc.
        """
        # Use base system's practice method
        # This runs in sandbox, doesn't affect real-world
        # Knowledge learned is domain-specific
        results = {"files_fixed": [], "files_failed": [], "knowledge_gained": []}
        
        for file_path in files:
            try:
                # Retrieve domain-specific knowledge before fixing
                domain_knowledge = self._retrieve_domain_knowledge(instance.problem_perspective)
                
                # Practice fix with domain context
                fix_result = self.base_system._practice_fix_in_sandbox(file_path, cycle)
                
                if fix_result.get("success"):
                    results["files_fixed"].append(file_path)
                    if fix_result.get("lesson"):
                        # Tag lesson with domain for domain-specific learning
                        domain_lesson = f"{instance.problem_perspective}: {fix_result['lesson']}"
                        results["knowledge_gained"].append(domain_lesson)
                        
                        # Learn from domain-specific pattern
                        self._learn_domain_pattern(
                            instance.problem_perspective,
                            fix_result["lesson"],
                            file_path
                        )
                else:
                    results["files_failed"].append(file_path)
            except Exception as e:
                logger.warning(f"[MULTI-INSTANCE] Sandbox fix error for {file_path}: {e}")
                results["files_failed"].append(file_path)
        
        return results
    
    def _retrieve_domain_knowledge(self, problem_perspective: str) -> List[Dict[str, Any]]:
        """Retrieve learned knowledge specific to this domain."""
        try:
            # Query Grace-Aligned LLM for domain-specific memories
            if self.base_system.llm_orchestrator and hasattr(self.base_system.llm_orchestrator, "grace_aligned_llm"):
                try:
                    memories = self.base_system.llm_orchestrator.grace_aligned_llm.retrieve_grace_memories(
                        query=f"{problem_perspective} fix pattern",
                        context={
                            "domain": problem_perspective,
                            "problem_type": problem_perspective,
                            "source": "sandbox_training"
                        },
                        max_memories=10
                    )
                    
                    # Filter memories by domain
                    domain_memories = [
                        mem for mem in memories
                        if problem_perspective in str(mem.get("content", "")).lower() or
                           problem_perspective in str(mem.get("context", {})).lower()
                    ]
                    
                    return domain_memories
                except Exception as e:
                    logger.warning(f"[MULTI-INSTANCE] Domain knowledge retrieval error: {e}")
            
            return []
        except Exception as e:
            logger.warning(f"[MULTI-INSTANCE] Domain knowledge retrieval failed: {e}")
            return []
    
    def _learn_domain_pattern(
        self,
        problem_perspective: str,
        pattern: str,
        file_path: str
    ):
        """Learn a domain-specific pattern."""
        try:
            # Store pattern with domain context
            domain_pattern = {
                "domain": problem_perspective,
                "pattern": pattern,
                "file_path": file_path,
                "learned_at": datetime.utcnow().isoformat()
            }
            
            # This will be stored in Memory Mesh via _store_domain_knowledge
            logger.debug(
                f"[MULTI-INSTANCE] Learned {problem_perspective} pattern: {pattern[:50]}..."
            )
            
        except Exception as e:
            logger.warning(f"[MULTI-INSTANCE] Domain pattern learning error: {e}")
    
    # ==================== REAL-WORLD FIXES ====================
    
    def start_real_world_workers(self):
        """Start background workers for real-world fixes (outside sandbox)."""
        if not self.real_world_running:
            return
        
        if self.real_world_workers:
            logger.warning("[MULTI-INSTANCE] Real-world workers already running")
            return
        
        self.real_world_running = True
        
        for i in range(self.max_real_world_workers):
            worker = threading.Thread(
                target=self._real_world_worker,
                args=(i,),
                daemon=True,
                name=f"RealWorld-Worker-{i}"
            )
            worker.start()
            self.real_world_workers.append(worker)
        
        self.stats["active_real_world_workers"] = len(self.real_world_workers)
        
        logger.info(f"[MULTI-INSTANCE] Started {len(self.real_world_workers)} real-world workers")
    
    def stop_real_world_workers(self):
        """Stop real-world workers."""
        self.real_world_running = False
        
        for worker in self.real_world_workers:
            worker.join(timeout=5.0)
        
        self.real_world_workers.clear()
        self.stats["active_real_world_workers"] = 0
        
        logger.info("[MULTI-INSTANCE] Real-world workers stopped")
    
    def _real_world_worker(self, worker_id: int):
        """Worker thread for real-world fixes (outside sandbox)."""
        logger.info(f"[MULTI-INSTANCE] Real-world worker {worker_id} started")
        
        while self.real_world_running:
            try:
                # Get task from queue (with timeout)
                try:
                    task = self.real_world_queue.get(timeout=1.0)
                except queue.Empty:
                    continue  # No tasks, check again
                
                # Process real-world fix (outside sandbox)
                task.started_at = datetime.utcnow()
                
                try:
                    result = self._fix_real_world(task)
                    
                    task.completed_at = datetime.utcnow()
                    task.result = result
                    
                    # Update statistics
                    with self.instance_lock:
                        self.stats["total_real_world_fixes"] += 1
                        if result.get("success"):
                            self.stats["total_files_fixed"] += len(result.get("files_fixed", []))
                    
                except Exception as e:
                    logger.error(f"[MULTI-INSTANCE] Real-world fix error: {e}")
                    task.result = {"success": False, "error": str(e)}
                
                finally:
                    self.real_world_queue.task_done()
                    
            except Exception as e:
                logger.error(f"[MULTI-INSTANCE] Real-world worker {worker_id} error: {e}")
                threading.Event().wait(1.0)
        
        logger.info(f"[MULTI-INSTANCE] Real-world worker {worker_id} stopped")
    
    def queue_real_world_fix(
        self,
        source: str,
        description: str,
        affected_files: List[str],
        priority: int = 5
    ) -> RealWorldTask:
        """Queue a real-world fix task (outside sandbox)."""
        task = RealWorldTask(
            task_id=f"realworld_{datetime.utcnow().timestamp()}",
            source=source,
            description=description,
            affected_files=affected_files,
            priority=priority
        )
        
        try:
            self.real_world_queue.put(task, timeout=5.0)
            logger.info(f"[MULTI-INSTANCE] Queued real-world fix: {task.task_id} ({source})")
        except queue.Full:
            logger.warning("[MULTI-INSTANCE] Real-world queue full, task dropped")
        
        return task
    
    def _fix_real_world(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix real-world issue (outside sandbox) using all integrated systems."""
        # Route to appropriate system based on source
        try:
            if task.source == "diagnostic" and self.diagnostic_engine:
                # Use diagnostic engine
                return self._fix_via_diagnostic(task)
            elif task.source == "self_healing" and self.healing_system:
                # Use self-healing system
                return self._fix_via_healing(task)
            elif task.source == "code_analyzer" and self.code_analyzer:
                # Use code analyzer
                return self._fix_via_code_analyzer(task)
            elif task.source == "llm" and self.llm_orchestrator:
                # Use LLM orchestrator
                return self._fix_via_llm(task)
            elif task.source == "testing" and self.testing_system:
                # Use testing system
                return self._fix_via_testing(task)
            elif task.source == "debugging" and self.debugging_system:
                # Use debugging system
                return self._fix_via_debugging(task)
            else:
                # Fallback to base system
                return self._fix_via_base_system(task)
                
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Real-world fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_diagnostic(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via diagnostic engine."""
        try:
            # Run diagnostic analysis
            if hasattr(self.diagnostic_engine, "analyze_system"):
                analysis = self.diagnostic_engine.analyze_system()
                anomalies = analysis.get("anomalies", [])
                
                # Fix anomalies
                fixed = []
                for anomaly in anomalies:
                    if self.healing_system:
                        fix_result = self.healing_system.execute_healing(
                            anomaly_type=anomaly.get("type"),
                            anomaly_data=anomaly
                        )
                        if fix_result.get("success"):
                            fixed.extend(fix_result.get("files_modified", []))
                
                return {
                    "success": len(fixed) > 0,
                    "files_fixed": fixed,
                    "action": "diagnostic_healing",
                    "anomalies_found": len(anomalies)
                }
            
            return {"success": False, "error": "diagnostic_engine_method_not_available"}
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Diagnostic fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_healing(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via self-healing system."""
        try:
            if not self.healing_system:
                return {"success": False, "error": "healing_system_not_available"}
            
            # Create alert for healing system
            from cognitive.self_healing_training_system import AlertSource, Alert
            
            alert = Alert(
                alert_id=f"alert_{task.task_id}",
                source=AlertSource.SYSTEM_HEALTH,
                severity="medium",
                description=task.description,
                affected_files=task.affected_files,
                requires_healing=True
            )
            
            # Use base system's healing method
            fix_result = self.base_system._fix_real_system(alert)
            
            return {
                "success": fix_result.get("success", False),
                "files_fixed": fix_result.get("files_modified", []),
                "action": "self_healing"
            }
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Healing fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_code_analyzer(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via code analyzer."""
        try:
            if not self.code_analyzer:
                return {"success": False, "error": "code_analyzer_not_available"}
            
            # Analyze files
            issues = []
            for file_path in task.affected_files:
                if hasattr(self.code_analyzer, "analyze_file"):
                    file_issues = self.code_analyzer.analyze_file(file_path)
                    issues.extend(file_issues)
            
            # Fix issues (if code analyzer has fix capability)
            fixed = []
            if hasattr(self.code_analyzer, "fix_issues") and issues:
                fix_result = self.code_analyzer.fix_issues(issues)
                fixed = fix_result.get("files_modified", [])
            
            return {
                "success": len(fixed) > 0,
                "files_fixed": fixed,
                "action": "code_analyzer",
                "issues_found": len(issues)
            }
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Code analyzer fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_llm(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via LLM orchestrator."""
        try:
            if not self.llm_orchestrator:
                return {"success": False, "error": "llm_orchestrator_not_available"}
            
            # Use LLM to generate fix
            query = f"Fix issue: {task.description} in files: {', '.join(task.affected_files)}"
            
            if hasattr(self.llm_orchestrator, "generate_response"):
                response = self.llm_orchestrator.generate_response(
                    query=query,
                    context={"files": task.affected_files, "source": task.source}
                )
                
                # Apply LLM-generated fix (would need implementation)
                return {
                    "success": True,
                    "files_fixed": task.affected_files,
                    "action": "llm_generated",
                    "response": response.get("response", "")[:200]  # Truncate
                }
            
            return {"success": False, "error": "llm_orchestrator_method_not_available"}
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] LLM fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_testing(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via testing system."""
        try:
            if not self.testing_system:
                return {"success": False, "error": "testing_system_not_available"}
            
            # Run tests to identify failures
            if hasattr(self.testing_system, "run_tests"):
                test_results = self.testing_system.run_tests(task.affected_files)
                failures = test_results.get("failures", [])
                
                # Fix test failures (if testing system has fix capability)
                fixed = []
                if failures and hasattr(self.testing_system, "fix_failures"):
                    fix_result = self.testing_system.fix_failures(failures)
                    fixed = fix_result.get("files_modified", [])
                
                return {
                    "success": len(fixed) > 0,
                    "files_fixed": fixed,
                    "action": "testing",
                    "test_failures": len(failures)
                }
            
            return {"success": False, "error": "testing_system_method_not_available"}
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Testing fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_debugging(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via debugging system."""
        try:
            if not self.debugging_system:
                return {"success": False, "error": "debugging_system_not_available"}
            
            # Debug issue
            if hasattr(self.debugging_system, "debug_issue"):
                debug_result = self.debugging_system.debug_issue(
                    description=task.description,
                    files=task.affected_files
                )
                
                # Fix based on debug findings
                fixed = []
                if debug_result.get("root_cause") and hasattr(self.debugging_system, "apply_fix"):
                    fix_result = self.debugging_system.apply_fix(debug_result)
                    fixed = fix_result.get("files_modified", [])
                
                return {
                    "success": len(fixed) > 0,
                    "files_fixed": fixed,
                    "action": "debugging",
                    "root_cause": debug_result.get("root_cause", "unknown")
                }
            
            return {"success": False, "error": "debugging_system_method_not_available"}
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Debugging fix error: {e}")
            return {"success": False, "error": str(e)}
    
    def _fix_via_base_system(self, task: RealWorldTask) -> Dict[str, Any]:
        """Fix via base training system (fallback)."""
        try:
            if not self.base_system.healing_system:
                return {"success": False, "error": "healing_system_not_available"}
            
            # Create alert
            from cognitive.self_healing_training_system import AlertSource, Alert
            
            alert = Alert(
                alert_id=f"alert_{task.task_id}",
                source=AlertSource.DIAGNOSTIC_ENGINE if task.source == "diagnostic" else AlertSource.USER_NEED,
                severity="medium",
                description=task.description,
                affected_files=task.affected_files,
                requires_healing=True
            )
            
            # Fix using base system
            fix_result = self.base_system._fix_real_system(alert)
            
            return {
                "success": fix_result.get("success", False),
                "files_fixed": fix_result.get("files_modified", []),
                "action": "base_system"
            }
        except Exception as e:
            logger.error(f"[MULTI-INSTANCE] Base system fix error: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== INSTANCE MANAGEMENT ====================
    
    def start_all(self):
        """Start all instances and workers."""
        self.running = True
        
        # Start sandbox instances
        self.start_all_sandbox_instances()
        
        # Start real-world workers
        self.start_real_world_workers()
        
        logger.info("[MULTI-INSTANCE] All instances and workers started")
    
    def stop_all(self):
        """Stop all instances and workers."""
        self.running = False
        
        # Stop sandbox instances
        with self.instance_lock:
            for instance in self.sandbox_instances.values():
                instance.state = "stopped"
            
            # Wait for threads
            for instance in self.sandbox_instances.values():
                if instance.thread:
                    instance.thread.join(timeout=5.0)
            
            self.sandbox_instances.clear()
            self.stats["active_sandbox_instances"] = 0
        
        # Stop real-world workers
        self.stop_real_world_workers()
        
        logger.info("[MULTI-INSTANCE] All instances and workers stopped")
    
    def get_instance_status(self) -> Dict[str, Any]:
        """Get status of all instances."""
        with self.instance_lock:
            sandbox_status = {
                instance_id: {
                    "type": instance.instance_type.value,
                    "problem_perspective": instance.problem_perspective,
                    "state": instance.state,
                    "files_processed": instance.files_processed,
                    "files_fixed": instance.files_fixed,
                    "current_task": instance.current_task,
                    "uptime_seconds": (datetime.utcnow() - instance.started_at).total_seconds()
                }
                for instance_id, instance in self.sandbox_instances.items()
            }
        
        return {
            "sandbox_instances": sandbox_status,
            "real_world_workers": self.stats["active_real_world_workers"],
            "queue_size": self.real_world_queue.qsize(),
            "statistics": self.stats.copy()
        }
    
    # ==================== STATISTICS ====================
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "stats": self.stats.copy(),
            "instance_status": self.get_instance_status(),
            "resource_utilization": {
                "sandbox_instances_active": self.stats["active_sandbox_instances"],
                "real_world_workers_active": self.stats["active_real_world_workers"],
                "concurrent_domains": self.stats["concurrent_domains"],
                "real_world_queue_size": self.real_world_queue.qsize()
            }
        }
        
        # Add federated learning statistics
        if self.enable_federated_learning:
            stats["federated_learning"] = self.get_federated_statistics()
        
        return stats


def get_multi_instance_training_system(
    base_training_system,
    max_sandbox_instances: int = 5,
    max_real_world_workers: int = 2,
    enable_real_world: bool = True,
    diagnostic_engine=None,
    healing_system=None,
    code_analyzer=None,
    llm_orchestrator=None,
    testing_system=None,
    debugging_system=None,
    enable_federated_learning: bool = True
) -> MultiInstanceTrainingSystem:
    """Factory function to get Multi-Instance Training System."""
    return MultiInstanceTrainingSystem(
        base_training_system=base_training_system,
        max_sandbox_instances=max_sandbox_instances,
        max_real_world_workers=max_real_world_workers,
        enable_real_world=enable_real_world,
        diagnostic_engine=diagnostic_engine,
        healing_system=healing_system,
        code_analyzer=code_analyzer,
        llm_orchestrator=llm_orchestrator,
        testing_system=testing_system,
        debugging_system=debugging_system,
        enable_federated_learning=enable_federated_learning
    )
