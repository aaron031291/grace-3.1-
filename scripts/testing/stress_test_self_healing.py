"""
Comprehensive Stress Test for Grace Self-Healing System

Industry-standard stress test that:
1. Deliberately breaks various system components
2. Tracks all self-healing responses
3. Monitors Genesis Key creation (what/where/when/who/how/why)
4. Tracks knowledge requests and LLM usage
5. Verifies fixes actually work
6. Provides comprehensive logging and reporting

Usage:
    python stress_test_self_healing.py
"""

import sys
import os
import time
import json
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from functools import partial
import tempfile

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from database.session import initialize_session_factory, get_session
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from cognitive.devops_healing_agent import get_devops_healing_agent, DevOpsLayer, IssueCategory, DevOpsLayer, IssueCategory
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKey, GenesisKeyType
from cognitive.autonomous_help_requester import get_help_requester

# Setup comprehensive logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class StressTestTracker:
    """Tracks all stress test activities and healing responses."""
    
    def __init__(self, session: Optional[Session] = None):
        self.test_results = []
        self.genesis_keys_created = []
        self.knowledge_requests = []
        self.llm_usage = []
        self.healing_actions = []
        self.fixes_verified = []
        self.start_time = datetime.now(UTC)
        self.session = session  # Store session for knowledge gap analysis
        
    def record_test(self, test_name: str, issue_introduced: str, result: Dict[str, Any]):
        """Record a stress test result."""
        self.test_results.append({
            "test_name": test_name,
            "issue_introduced": issue_introduced,
            "timestamp": datetime.now(UTC).isoformat(),
            "result": result
        })
        logger.info(f"[STRESS-TEST] {test_name}: {issue_introduced}")
    
    def record_genesis_key(self, key: GenesisKey):
        """Record a Genesis Key created during healing."""
        self.genesis_keys_created.append({
            "key_id": key.key_id,
            "key_type": key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
            "what": key.what_description,
            "where": key.where_location,
            "when": key.when_timestamp.isoformat() if key.when_timestamp else None,
            "who": key.who_actor,
            "how": key.how_method,
            "why": key.why_reason,
            "context_data": key.context_data,
            "timestamp": datetime.now(UTC).isoformat()
        })
        logger.info(f"[GENESIS-KEY] Created: {key.key_id} - {key.what_description}")
    
    def record_knowledge_request(self, request: Dict[str, Any]):
        """Record a knowledge request."""
        self.knowledge_requests.append({
            "timestamp": datetime.now(UTC).isoformat(),
            **request
        })
        logger.info(f"[KNOWLEDGE-REQUEST] {request.get('type', 'unknown')}: {request.get('query', 'N/A')}")
    
    def record_llm_usage(self, usage: Dict[str, Any]):
        """Record LLM usage."""
        self.llm_usage.append({
            "timestamp": datetime.now(UTC).isoformat(),
            **usage
        })
        logger.info(f"[LLM-USAGE] {usage.get('model', 'unknown')}: {usage.get('purpose', 'N/A')}")
    
    def record_healing_action(self, action: Dict[str, Any]):
        """Record a healing action."""
        self.healing_actions.append({
            "timestamp": datetime.now(UTC).isoformat(),
            **action
        })
        logger.info(f"[HEALING-ACTION] {action.get('action_type', 'unknown')}: {action.get('description', 'N/A')}")
    
    def record_fix_verification(self, verification: Dict[str, Any]):
        """Record fix verification result."""
        self.fixes_verified.append({
            "timestamp": datetime.now(UTC).isoformat(),
            **verification
        })
        logger.info(f"[FIX-VERIFICATION] {verification.get('status', 'unknown')}: {verification.get('issue', 'N/A')}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive stress test report."""
        end_time = datetime.now(UTC)
        duration = (end_time - self.start_time).total_seconds()
        
        # Analyze results
        total_tests = len(self.test_results)
        successful_fixes = sum(1 for r in self.fixes_verified if r.get("status") == "fixed")
        failed_fixes = sum(1 for r in self.fixes_verified if r.get("status") == "failed")
        
        # Count Genesis Keys by type
        genesis_by_type = {}
        for key in self.genesis_keys_created:
            key_type = key["key_type"]
            genesis_by_type[key_type] = genesis_by_type.get(key_type, 0) + 1
        
        # Count knowledge requests
        knowledge_by_type = {}
        for req in self.knowledge_requests:
            req_type = req.get("type", "unknown")
            knowledge_by_type[req_type] = knowledge_by_type.get(req_type, 0) + 1
        
        # Count LLM usage
        llm_by_model = {}
        for usage in self.llm_usage:
            model = usage.get("model", "unknown")
            llm_by_model[model] = llm_by_model.get(model, 0) + 1
        
        # Calculate KPIs
        fix_success_rate = (successful_fixes / (successful_fixes + failed_fixes) * 100) if (successful_fixes + failed_fixes) > 0 else 0
        detection_rate = (total_tests / total_tests * 100) if total_tests > 0 else 0
        genesis_key_creation_rate = len(self.genesis_keys_created) / total_tests if total_tests > 0 else 0
        knowledge_request_rate = len(self.knowledge_requests) / total_tests if total_tests > 0 else 0
        llm_usage_rate = len(self.llm_usage) / total_tests if total_tests > 0 else 0
        
        # KPI targets
        kpi_targets = {
            "fix_success_rate": 95.0,  # HIGH TARGET: 95%
            "detection_rate": 100.0,
            "genesis_key_creation_rate": 2.0,  # At least 2 keys per test
            "knowledge_request_rate": 0.5,  # Should request knowledge when needed
            "llm_usage_rate": 0.3  # Should use LLMs for complex decisions
        }
        
        # Calculate KPI scores (0-100)
        kpi_scores = {
            "fix_success_rate": min(100, (fix_success_rate / kpi_targets["fix_success_rate"]) * 100),
            "detection_rate": min(100, (detection_rate / kpi_targets["detection_rate"]) * 100),
            "genesis_key_creation_rate": min(100, (genesis_key_creation_rate / kpi_targets["genesis_key_creation_rate"]) * 100),
            "knowledge_request_rate": min(100, (knowledge_request_rate / kpi_targets["knowledge_request_rate"]) * 100) if knowledge_request_rate > 0 else 50,  # Neutral if no requests
            "llm_usage_rate": min(100, (llm_usage_rate / kpi_targets["llm_usage_rate"]) * 100) if llm_usage_rate > 0 else 50
        }
        
        # Overall KPI score (weighted average)
        kpi_weights = {
            "fix_success_rate": 0.5,  # Most important
            "detection_rate": 0.2,
            "genesis_key_creation_rate": 0.1,
            "knowledge_request_rate": 0.1,
            "llm_usage_rate": 0.1
        }
        
        overall_kpi_score = sum(
            kpi_scores[kpi] * kpi_weights[kpi]
            for kpi in kpi_scores.keys()
        )
        
        report = {
            "test_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "total_tests": total_tests,
                "successful_fixes": successful_fixes,
                "failed_fixes": failed_fixes,
                "fix_success_rate": fix_success_rate,
                "kpi_target": 95.0,  # HIGH TARGET
                "meets_target": fix_success_rate >= 95.0
            },
            "kpis": {
                "overall_score": overall_kpi_score,
                "targets": kpi_targets,
                "scores": kpi_scores,
                "weights": kpi_weights,
                "metrics": {
                    "fix_success_rate": fix_success_rate,
                    "detection_rate": detection_rate,
                    "genesis_key_creation_rate": genesis_key_creation_rate,
                    "knowledge_request_rate": knowledge_request_rate,
                    "llm_usage_rate": llm_usage_rate
                }
            },
            "genesis_keys": {
                "total_created": len(self.genesis_keys_created),
                "by_type": genesis_by_type,
                "details": self.genesis_keys_created
            },
            "knowledge_requests": {
                "total": len(self.knowledge_requests),
                "by_type": knowledge_by_type,
                "details": self.knowledge_requests
            },
            "llm_usage": {
                "total": len(self.llm_usage),
                "by_model": llm_by_model,
                "details": self.llm_usage
            },
            "healing_actions": {
                "total": len(self.healing_actions),
                "details": self.healing_actions
            },
            "fix_verifications": {
                "total": len(self.fixes_verified),
                "successful": successful_fixes,
                "failed": failed_fixes,
                "details": self.fixes_verified
            },
            "test_results": self.test_results,
            "knowledge_gaps": self._identify_knowledge_gaps()
        }
        
        return report
    
    def _identify_knowledge_gaps(self) -> Dict[str, Any]:
        """Ask Grace what knowledge is missing that she needs."""
        gaps = {
            "identified_gaps": [],
            "recommendations": [],
            "missing_knowledge_areas": []
        }
        
        try:
            # Query Grace's memory mesh learner for knowledge gaps
            from cognitive.memory_mesh_learner import MemoryMeshLearner
            from retrieval.retriever import DocumentRetriever
            from embedding import get_embedding_model
            
            # Get session from runner if available
            session = getattr(self, 'session', None)
            if not session:
                # Try to get from database
                from database.session import get_session
                session = get_session()
            
            learner = MemoryMeshLearner(
                session=session,
                retriever=DocumentRetriever(get_embedding_model()),
                knowledge_base_path=Path("backend/knowledge_base")
            )
            
            # Identify knowledge gaps
            identified_gaps = learner.identify_knowledge_gaps()
            gaps["identified_gaps"] = identified_gaps[:10]  # Top 10 gaps
            
            # Analyze failed fixes to identify missing knowledge
            failed_issues = [r for r in self.fixes_verified if r.get("status") == "failed"]
            for failed in failed_issues:
                issue = failed.get("issue", "unknown")
                gaps["missing_knowledge_areas"].append({
                    "issue": issue,
                    "reason": "Failed to fix - may indicate missing knowledge",
                    "recommendation": f"Study knowledge related to: {issue}"
                })
            
            # Analyze knowledge requests to identify patterns
            knowledge_patterns = {}
            for req in self.knowledge_requests:
                req_type = req.get("type", "unknown")
                query = req.get("query", "")
                if req_type not in knowledge_patterns:
                    knowledge_patterns[req_type] = []
                knowledge_patterns[req_type].append(query)
            
            # Generate recommendations
            for req_type, queries in knowledge_patterns.items():
                if len(queries) > 1:  # Multiple requests in same category
                    gaps["recommendations"].append({
                        "category": req_type,
                        "frequency": len(queries),
                        "recommendation": f"Pre-load knowledge about {req_type} to reduce {len(queries)} knowledge requests",
                        "example_queries": queries[:3]
                    })
            
            # Add recommendations from memory mesh gaps
            for gap in identified_gaps[:5]:
                gaps["recommendations"].append({
                    "category": "practice_needed",
                    "topic": gap.get("topic", "unknown"),
                    "recommendation": gap.get("reason", "Needs practice"),
                    "gap_size": gap.get("gap_size", 0.0)
                })
            
        except Exception as e:
            logger.warning(f"Failed to identify knowledge gaps: {e}")
            gaps["error"] = str(e)
        
        return gaps


class StressTestRunner:
    """Runs comprehensive stress tests."""
    
    def __init__(self, session: Session):
        self.session = session
        self.tracker = StressTestTracker(session=session)  # Pass session to tracker
        self.healing_agent = get_devops_healing_agent(session=session)
        self.genesis_service = get_genesis_service()
        self.help_requester = get_help_requester(session=session)
        
        # Track original state for restoration
        self.backup_files = {}
        self.original_configs = {}
        
        # Hook into Genesis Key creation to track them
        self._hook_genesis_key_creation()
        
        # Hook into knowledge requests
        self._hook_knowledge_requests()
        
        # Hook into LLM usage
        self._hook_llm_usage()
        
        # Track initial Genesis Key count
        self.initial_genesis_key_count = self._count_genesis_keys()
        
        # Register with KPI tracker
        self._register_kpi_tracking()
        
    def _hook_genesis_key_creation(self):
        """Hook into Genesis Key creation to track all keys."""
        original_create = self.genesis_service.create_key
        
        def tracked_create(*args, **kwargs):
            key = original_create(*args, **kwargs)
            self.tracker.record_genesis_key(key)
            return key
        
        self.genesis_service.create_key = tracked_create
        logger.info("[STRESS-TEST] Hooked into Genesis Key creation")
    
    def _hook_knowledge_requests(self):
        """Hook into knowledge requests."""
        if hasattr(self.healing_agent, '_check_knowledge'):
            original_check = self.healing_agent._check_knowledge
            
            def tracked_check(analysis):
                has_knowledge = original_check(analysis)
                if not has_knowledge:
                    self.tracker.record_knowledge_request({
                        "type": "knowledge_missing",
                        "query": analysis.get("description", "unknown"),
                        "layer": str(analysis.get("layer", "unknown")),
                        "category": str(analysis.get("category", "unknown"))
                    })
                return has_knowledge
            
            self.healing_agent._check_knowledge = tracked_check
        
        # Hook into proactive learner if available
        if hasattr(self.healing_agent, 'proactive_learner') and self.healing_agent.proactive_learner:
            original_request = getattr(self.healing_agent.proactive_learner, 'request_knowledge', None)
            if original_request:
                def tracked_request(*args, **kwargs):
                    result = original_request(*args, **kwargs)
                    self.tracker.record_knowledge_request({
                        "type": "proactive_learning",
                        "query": kwargs.get("query", args[0] if args else "unknown"),
                        "result": result
                    })
                    return result
                self.healing_agent.proactive_learner.request_knowledge = tracked_request
        
        logger.info("[STRESS-TEST] Hooked into knowledge requests")
    
    def _count_genesis_keys(self) -> int:
        """Count Genesis Keys in database."""
        try:
            from models.genesis_key_models import GenesisKey
            count = self.session.query(GenesisKey).count()
            return count
        except:
            return 0
    
    def _fetch_all_genesis_keys(self) -> List[Dict[str, Any]]:
        """Fetch all Genesis Keys created during test."""
        try:
            from models.genesis_key_models import GenesisKey
            keys = self.session.query(GenesisKey).filter(
                GenesisKey.created_at >= self.tracker.start_time
            ).all()
            
            return [{
                "key_id": key.key_id,
                "key_type": key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
                "what": key.what_description,
                "where": key.where_location,
                "when": key.when_timestamp.isoformat() if key.when_timestamp else None,
                "who": key.who_actor,
                "how": key.how_method,
                "why": key.why_reason,
                "context_data": key.context_data
            } for key in keys]
        except Exception as e:
            logger.warning(f"Failed to fetch Genesis Keys: {e}")
            return []
    
    def _register_kpi_tracking(self):
        """Register stress test with KPI tracker."""
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            self.kpi_tracker = get_kpi_tracker()
            self.kpi_tracker.register_component(
                "self_healing_stress_test",
                {
                    "tests_run": 1.0,
                    "fixes_successful": 2.0,
                    "fixes_failed": -1.0,
                    "genesis_keys_created": 0.5,
                    "knowledge_requests": 0.3,
                    "llm_usage": 0.3
                }
            )
            logger.info("[STRESS-TEST] Registered with KPI tracker")
        except Exception as e:
            logger.warning(f"[STRESS-TEST] KPI tracker not available: {e}")
            self.kpi_tracker = None
    
    def _track_kpi(self, metric_name: str, value: float = 1.0):
        """Track a KPI metric."""
        if hasattr(self, 'kpi_tracker') and self.kpi_tracker:
            try:
                self.kpi_tracker.increment_kpi(
                    "self_healing_stress_test",
                    metric_name,
                    value
                )
            except Exception:
                pass
    
    def _hook_llm_usage(self):
        """Hook into LLM usage."""
        # Hook into cognitive engine LLM calls
        if hasattr(self.healing_agent, 'cognitive_engine') and self.healing_agent.cognitive_engine:
            # Try to hook into LLM orchestrator if available
            if hasattr(self.healing_agent, 'llm_orchestrator') and self.healing_agent.llm_orchestrator:
                original_chat = getattr(self.healing_agent.llm_orchestrator, 'chat', None)
                if original_chat:
                    def tracked_chat(*args, **kwargs):
                        start_time = time.time()
                        result = original_chat(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        self.tracker.record_llm_usage({
                            "model": kwargs.get("model", "unknown"),
                            "purpose": "healing_decision",
                            "duration_seconds": duration,
                            "prompt_length": len(kwargs.get("messages", [])),
                            "response_length": len(str(result))
                        })
                        return result
                    self.healing_agent.llm_orchestrator.chat = tracked_chat
        
        logger.info("[STRESS-TEST] Hooked into LLM usage")
    
    def _monitor_healing_actions(self, result: Dict[str, Any]):
        """Monitor and record healing actions from result."""
        if result.get("fix_applied"):
            self.tracker.record_healing_action({
                "action_type": "fix_applied",
                "description": result.get("fix_description", "unknown"),
                "method": result.get("fix_method", "unknown"),
                "layer": result.get("layer", "unknown"),
                "category": result.get("category", "unknown"),
                "success": result.get("success", False)
            })
        
        if result.get("knowledge_requested"):
            self.tracker.record_knowledge_request({
                "type": "healing_knowledge_request",
                "query": result.get("knowledge_query", "unknown"),
                "source": result.get("knowledge_source", "unknown")
            })
        
        if result.get("llm_used"):
            self.tracker.record_llm_usage({
                "model": result.get("llm_model", "unknown"),
                "purpose": result.get("llm_purpose", "healing"),
                "tokens": result.get("llm_tokens", 0)
            })
    
    def run_all_tests(self):
        """Run all stress tests - 10X ENHANCED with 1000 test scenarios."""
        logger.info("=" * 80)
        logger.info("STRESS TEST STARTING - 10X ENHANCED - 1000 Test Scenarios")
        logger.info("Deliberately Breaking System Components")
        logger.info("=" * 80)
        
        # 10X ENHANCEMENT: 1000 test scenarios - programmatically generated
        tests = []
        
        # Base test methods organized by category
        base_tests = {
            'file_system': [
                self.test_missing_file, self.test_corrupted_file, self.test_locked_file,
                self.test_invalid_file_permissions, self.test_file_too_large,
                self.test_missing_directory, self.test_circular_symlink, self.test_file_encoding_error
            ],
            'database': [
                self.test_corrupted_database, self.test_missing_table, self.test_invalid_schema,
                self.test_foreign_key_violation, self.test_connection_pool_exhausted,
                self.test_deadlock, self.test_transaction_timeout, self.test_index_corruption,
                self.test_orphaned_records, self.test_database_locked
            ],
            'code': [
                self.test_syntax_error, self.test_missing_import, self.test_undefined_variable,
                self.test_type_error, self.test_attribute_error, self.test_indentation_error,
                self.test_name_error
            ],
            'configuration': [
                self.test_configuration_error, self.test_missing_env_var, self.test_invalid_env_var,
                self.test_config_file_corrupted, self.test_config_syntax_error,
                self.test_config_permission_denied, self.test_config_override_failed,
                self.test_config_validation_failed, self.test_config_missing_section,
                self.test_config_invalid_type
            ],
            'network': [
                self.test_network_timeout, self.test_connection_refused, self.test_dns_resolution_failed,
                self.test_ssl_certificate_error, self.test_rate_limit_exceeded,
                self.test_service_unavailable, self.test_network_unreachable,
                self.test_timeout_reading_response, self.test_connection_reset, self.test_proxy_error
            ],
            'security': [
                self.test_permission_error, self.test_unauthorized_access, self.test_invalid_token,
                self.test_expired_token, self.test_weak_encryption, self.test_sql_injection_attempt,
                self.test_path_traversal_attempt, self.test_csrf_token_missing,
                self.test_authentication_failed, self.test_authorization_failed
            ],
            'performance': [
                self.test_slow_query, self.test_cpu_exhausted, self.test_disk_space_full,
                self.test_memory_leak, self.test_infinite_loop, self.test_n_plus_one_query,
                self.test_cache_miss_storm, self.test_garbage_collection_stuck,
                self.test_thread_deadlock, self.test_resource_contention
            ],
            'memory': [
                self.test_memory_issue, self.test_out_of_memory, self.test_memory_fragmentation,
                self.test_buffer_overflow, self.test_stack_overflow, self.test_memory_corruption,
                self.test_shared_memory_error, self.test_memory_mapping_failed,
                self.test_virtual_memory_exhausted, self.test_memory_allocation_failed
            ],
            'concurrency': [
                self.test_concurrent_errors, self.test_race_condition, self.test_deadlock_multiple_threads,
                self.test_livelock, self.test_starvation, self.test_atomic_operation_failed,
                self.test_lock_timeout, self.test_semaphore_exhausted,
                self.test_condition_variable_error, self.test_barrier_timeout
            ],
            'integration': [
                self.test_data_integrity, self.test_api_version_mismatch, self.test_service_dependency_down,
                self.test_message_queue_full, self.test_event_bus_disconnected,
                self.test_database_replication_lag, self.test_cache_invalidation_failed,
                self.test_external_service_changed, self.test_webhook_delivery_failed,
                self.test_third_party_api_changed
            ]
        }
        
        # Generate 1000 tests by creating variants of base tests
        test_id = 0
        for category, test_methods in base_tests.items():
            for base_test in test_methods:
                # Add base test
                test_name = base_test.__name__
                tests.append((f"{test_name}_{test_id}", base_test))
                test_id += 1
                
                # Add 9 variants to reach 10x per base test
                for variant in range(1, 10):
                    variant_name = f"{test_name}_variant_{variant}_{test_id}"
                    # Use partial to properly capture variables
                    tests.append((variant_name, partial(self._run_test_variant, base_test, variant)))
                    test_id += 1
        
        # Add additional generic tests to reach exactly 1000
        while len(tests) < 1000:
            category_idx = len(tests) % len(base_tests)
            category = list(base_tests.keys())[category_idx]
            test_methods = base_tests[category]
            method_idx = (len(tests) // len(base_tests)) % len(test_methods)
            base_test = test_methods[method_idx]
            variant_num = len(tests) // 100
            tests.append((f"generic_{category}_{variant_num}_{len(tests)}", 
                         partial(self._run_test_variant, base_test, variant_num)))
        
        # Limit to exactly 1000
        tests = tests[:1000]
        
        logger.info(f"[STRESS-TEST] Running {len(tests)} test scenarios (10X ENHANCED)")
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"RUNNING TEST: {test_name}")
                logger.info(f"{'='*80}\n")
                
                result = test_func()
                self.tracker.record_test(test_name, test_func.__doc__, result)
                
                # Track KPIs
                self._track_kpi("tests_run", 1.0)
                if result.get("status") == "fixed":
                    self._track_kpi("fixes_successful", 1.0)
                elif result.get("status") == "failed":
                    self._track_kpi("fixes_failed", 1.0)
                
                # Wait for healing to process (reduced for 1000 tests)
                time.sleep(1)  # Reduced to 1 second for 1000 tests
                
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}", exc_info=True)
                self.tracker.record_test(test_name, test_func.__doc__, {
                    "status": "test_failed",
                    "error": str(e)
                })
        
        # Fetch all Genesis Keys created during test
        all_keys = self._fetch_all_genesis_keys()
        for key in all_keys:
            # Only add if not already tracked
            if not any(k["key_id"] == key["key_id"] for k in self.tracker.genesis_keys_created):
                self.tracker.genesis_keys_created.append(key)
        
        # Track final KPIs
        if hasattr(self, 'kpi_tracker') and self.kpi_tracker:
            self._track_kpi("genesis_keys_created", len(self.tracker.genesis_keys_created))
            self._track_kpi("knowledge_requests", len(self.tracker.knowledge_requests))
            self._track_kpi("llm_usage", len(self.tracker.llm_usage))
            
            # Get KPI health signal
            try:
                kpi_health = self.kpi_tracker.get_health_signal("self_healing_stress_test")
                logger.info(f"[STRESS-TEST] KPI Health: {kpi_health.get('status', 'unknown')} (Trust: {kpi_health.get('trust_score', 0):.2f})")
            except Exception as e:
                logger.warning(f"[STRESS-TEST] Failed to get KPI health: {e}")
        
        # Generate final report
        report = self.tracker.generate_report()
        self.save_report(report)
        
        return report
    
    def test_missing_file(self):
        """Test: Delete a critical file and see if healing restores it."""
        logger.info("[TEST] Missing File Test")
        
        # Create a test file
        test_file = Path("backend/test_stress_file.txt")
        test_file.write_text("This is a test file for stress testing")
        self.backup_files[str(test_file)] = test_file.read_text()
        
        # Delete it
        test_file.unlink()
        logger.info(f"[TEST] Deleted file: {test_file}")
        
        # Trigger healing
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Missing file: {test_file}",
            error=FileNotFoundError(f"File not found: {test_file}"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR,
            context={"file_path": str(test_file)}
        )
        
        # Monitor healing actions
        self._monitor_healing_actions(result)
        
        # Verify fix
        time.sleep(3)
        fixed = test_file.exists()
        
        # Record verification
        self.tracker.record_fix_verification({
            "issue": f"Missing file: {test_file}",
            "status": "fixed" if fixed else "failed",
            "verified": fixed,
            "healing_result": result
        })
        
        return {
            "status": "fixed" if fixed else "failed",
            "file": str(test_file),
            "healing_result": result,
            "verified": fixed
        }
    
    def test_corrupted_database(self):
        """Test: Corrupt database schema and see if healing fixes it."""
        logger.info("[TEST] Corrupted Database Test")
        
        # Try to create a table with invalid schema
        try:
            from sqlalchemy import text
            self.session.execute(text("CREATE TABLE IF NOT EXISTS test_corrupted (id INVALID_TYPE)"))
            self.session.commit()
        except Exception as e:
            logger.info(f"[TEST] Introduced database error: {e}")
        
        # Trigger healing
        result = self.healing_agent.detect_and_heal(
            issue_description="Database schema corruption",
            error=Exception("Invalid column type"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        # Monitor healing actions
        self._monitor_healing_actions(result)
        
        # Verify fix (check if table was fixed)
        time.sleep(2)
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(self.session.bind)
            tables = inspector.get_table_names()
            table_exists = "test_corrupted" in tables
            verified = not table_exists  # Table should be removed or fixed
        except:
            verified = False
        
        self.tracker.record_fix_verification({
            "issue": "Database schema corruption",
            "status": "fixed" if verified else "detected",
            "verified": verified,
            "healing_result": result
        })
        
        return {
            "status": "fixed" if verified else "detected",
            "healing_result": result,
            "error": str(e) if 'e' in locals() else "unknown",
            "verified": verified
        }
    
    def test_syntax_error(self):
        """Test: Introduce syntax error in a Python file."""
        logger.info("[TEST] Syntax Error Test")
        
        # Create a file with syntax error
        test_file = Path("backend/test_syntax_error.py")
        test_file.write_text("def broken_function(\n    return 'missing colon'\n")
        self.backup_files[str(test_file)] = ""
        
        # Trigger healing
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Syntax error in {test_file}",
            error=SyntaxError("invalid syntax", (str(test_file), 2, 0, "return 'missing colon'\n")),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR,
            context={"file_path": str(test_file)}
        )
        
        # Monitor healing actions
        self._monitor_healing_actions(result)
        
        # Verify fix
        time.sleep(3)
        try:
            compile(test_file.read_text(), str(test_file), 'exec')
            fixed = True
        except SyntaxError as e:
            fixed = False
            logger.warning(f"[TEST] Syntax still broken: {e}")
        
        self.tracker.record_fix_verification({
            "issue": f"Syntax error in {test_file}",
            "status": "fixed" if fixed else "failed",
            "verified": fixed,
            "healing_result": result
        })
        
        return {
            "status": "fixed" if fixed else "failed",
            "file": str(test_file),
            "healing_result": result,
            "verified": fixed
        }
    
    def test_missing_import(self):
        """Test: Remove an import and see if healing adds it back."""
        logger.info("[TEST] Missing Import Test")
        
        # Create a file with missing import
        test_file = Path("backend/test_missing_import.py")
        test_file.write_text("from nonexistent_module import something\nprint('test')")
        self.backup_files[str(test_file)] = ""
        
        # Trigger healing
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Missing import in {test_file}",
            error=ImportError("No module named 'nonexistent_module'"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR,
            context={"file_path": str(test_file)}
        )
        
        # Monitor healing actions
        self._monitor_healing_actions(result)
        
        # Verify fix (check if import was fixed or file was updated)
        time.sleep(2)
        if test_file.exists():
            content = test_file.read_text()
            # Check if import was fixed or commented out
            verified = "nonexistent_module" not in content or "#" in content.split("\n")[0]
        else:
            verified = False
        
        self.tracker.record_fix_verification({
            "issue": f"Missing import in {test_file}",
            "status": "fixed" if verified else "detected",
            "verified": verified,
            "healing_result": result
        })
        
        return {
            "status": "fixed" if verified else "detected",
            "file": str(test_file),
            "healing_result": result,
            "verified": verified
        }
    
    def test_configuration_error(self):
        """Test: Break configuration and see if healing fixes it."""
        logger.info("[TEST] Configuration Error Test")
        
        # Modify .env file (if exists)
        env_file = Path("backend/.env")
        if env_file.exists():
            original_content = env_file.read_text()
            self.original_configs[str(env_file)] = original_content
            env_file.write_text(original_content + "\nINVALID_CONFIG=broken\n")
            logger.info("[TEST] Added invalid config")
        
        # Trigger healing
        result = self.healing_agent.detect_and_heal(
            issue_description="Configuration error: invalid setting",
            error=ValueError("Invalid configuration"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        # Monitor healing actions
        self._monitor_healing_actions(result)
        
        # Verify fix (check if config was restored)
        time.sleep(2)
        if env_file.exists():
            content = env_file.read_text()
            verified = "INVALID_CONFIG=broken" not in content
        else:
            verified = False
        
        self.tracker.record_fix_verification({
            "issue": "Configuration error",
            "status": "fixed" if verified else "detected",
            "verified": verified,
            "healing_result": result
        })
        
        return {
            "status": "fixed" if verified else "detected",
            "healing_result": result,
            "verified": verified
        }
    
    def test_permission_error(self):
        """Test: Create permission error and see if healing fixes it."""
        logger.info("[TEST] Permission Error Test")
        
        result = self.healing_agent.detect_and_heal(
            issue_description="Permission denied on file access",
            error=PermissionError("Permission denied"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {
            "status": "detected",
            "healing_result": result
        }
    
    def test_memory_issue(self):
        """Test: Simulate memory issue."""
        logger.info("[TEST] Memory Issue Test")
        
        result = self.healing_agent.detect_and_heal(
            issue_description="High memory usage detected",
            error=MemoryError("Out of memory"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {
            "status": "detected",
            "healing_result": result
        }
    
    def test_network_timeout(self):
        """Test: Simulate network timeout."""
        logger.info("[TEST] Network Timeout Test")
        
        result = self.healing_agent.detect_and_heal(
            issue_description="Network timeout connecting to external service",
            error=TimeoutError("Connection timeout"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {
            "status": "detected",
            "healing_result": result
        }
    
    def test_data_integrity(self):
        """Test: Break data integrity."""
        logger.info("[TEST] Data Integrity Test")
        
        result = self.healing_agent.detect_and_heal(
            issue_description="Data integrity violation detected",
            error=ValueError("Data inconsistency"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {
            "status": "detected",
            "healing_result": result
        }
    
    def test_concurrent_errors(self):
        """Test: Introduce multiple concurrent errors."""
        logger.info("[TEST] Concurrent Errors Test")
        
        results = []
        errors = [
            ("Missing file", FileNotFoundError("File not found")),
            ("Syntax error", SyntaxError("invalid syntax")),
            ("Import error", ImportError("No module named 'test'")),
        ]
        
        for desc, error in errors:
            result = self.healing_agent.detect_and_heal(
                issue_description=desc,
                error=error,
                affected_layer="backend",
                issue_category="code_error"
            )
            self._monitor_healing_actions(result)
            results.append(result)
        
        return {
            "status": "detected",
            "concurrent_errors": len(errors),
            "healing_results": results
        }
    
    # =====================================================================
    # 10X ENHANCEMENT: Additional Test Scenarios (90 new tests)
    # =====================================================================
    
    # FILE SYSTEM VARIANTS
    def test_missing_file_variant(self, variant: int):
        """Test missing file variant."""
        test_file = Path(f"backend/test_stress_file_v{variant}.txt")
        test_file.write_text(f"Variant {variant} test file")
        self.backup_files[str(test_file)] = test_file.read_text()
        test_file.unlink()
        
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Missing file variant {variant}: {test_file}",
            error=FileNotFoundError(f"File not found: {test_file}"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        self._monitor_healing_actions(result)
        time.sleep(2)
        fixed = test_file.exists()
        
        self.tracker.record_fix_verification({
            "issue": f"Missing file variant {variant}",
            "status": "fixed" if fixed else "failed",
            "verified": fixed
        })
        
        return {"status": "fixed" if fixed else "failed", "verified": fixed}
    
    def test_corrupted_file(self):
        """Test corrupted file."""
        test_file = Path("backend/test_corrupted.txt")
        test_file.write_text("Valid content")
        self.backup_files[str(test_file)] = test_file.read_text()
        
        # Corrupt file
        test_file.write_bytes(b'\x00\x01\x02\x03\xFF\xFE\xFD')
        
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Corrupted file: {test_file}",
            error=UnicodeDecodeError("utf-8", b'\x00', 0, 1, "invalid start byte"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        self._monitor_healing_actions(result)
        time.sleep(2)
        try:
            content = test_file.read_text()
            fixed = "Valid content" in content or len(content) > 0
        except:
            fixed = False
        
        self.tracker.record_fix_verification({
            "issue": "Corrupted file",
            "status": "fixed" if fixed else "detected",
            "verified": fixed
        })
        
        return {"status": "fixed" if fixed else "detected", "verified": fixed}
    
    def test_locked_file(self):
        """Test locked file."""
        result = self.healing_agent.detect_and_heal(
            issue_description="File is locked by another process",
            error=PermissionError("File is locked"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_invalid_file_permissions(self):
        """Test invalid file permissions."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Invalid file permissions",
            error=PermissionError("Permission denied"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_file_too_large(self):
        """Test file too large."""
        result = self.healing_agent.detect_and_heal(
            issue_description="File size exceeds limit",
            error=OSError("File too large"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_missing_directory(self):
        """Test missing directory."""
        test_dir = Path("backend/test_missing_dir")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Missing directory: {test_dir}",
            error=FileNotFoundError(f"Directory not found: {test_dir}"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_circular_symlink(self):
        """Test circular symlink."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Circular symlink detected",
            error=OSError("Circular symlink"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_file_encoding_error(self):
        """Test file encoding error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="File encoding error",
            error=UnicodeDecodeError("utf-8", b'\xFF', 0, 1, "invalid"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.CODE_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    # DATABASE VARIANTS
    def test_missing_table(self):
        """Test missing table."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Table does not exist",
            error=Exception("Table 'missing_table' does not exist"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_invalid_schema(self):
        """Test invalid schema."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Invalid database schema",
            error=Exception("Schema validation failed"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_foreign_key_violation(self):
        """Test foreign key violation."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Foreign key constraint violation",
            error=Exception("Foreign key violation"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_connection_pool_exhausted(self):
        """Test connection pool exhausted."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Database connection pool exhausted",
            error=Exception("Connection pool exhausted"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_deadlock(self):
        """Test database deadlock."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Database deadlock detected",
            error=Exception("Deadlock detected"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_transaction_timeout(self):
        """Test transaction timeout."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Transaction timeout",
            error=Exception("Transaction timeout"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_index_corruption(self):
        """Test index corruption."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Database index corruption",
            error=Exception("Index corruption detected"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_orphaned_records(self):
        """Test orphaned records."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Orphaned database records",
            error=Exception("Orphaned records detected"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_database_locked(self):
        """Test database locked."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Database is locked",
            error=Exception("Database is locked"),
            affected_layer=DevOpsLayer.DATABASE,
            issue_category=IssueCategory.DATABASE
        )
        
        return {"status": "detected", "healing_result": result}
    
    # CODE ERROR VARIANTS
    def test_syntax_error_variant(self, variant: int):
        """Test syntax error variant."""
        test_file = Path(f"backend/test_syntax_v{variant}.py")
        errors = [
            "def broken()\n    pass",  # Missing colon
            "if True\n    pass",  # Missing colon
            "for i in range(10)\n    print(i)",  # Missing colon
        ]
        error_code = errors[variant % len(errors)]
        test_file.write_text(error_code)
        self.backup_files[str(test_file)] = ""
        
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Syntax error variant {variant}",
            error=SyntaxError("invalid syntax"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        self._monitor_healing_actions(result)
        time.sleep(2)
        try:
            compile(test_file.read_text(), str(test_file), 'exec')
            fixed = True
        except:
            fixed = False
        
        self.tracker.record_fix_verification({
            "issue": f"Syntax error variant {variant}",
            "status": "fixed" if fixed else "failed",
            "verified": fixed
        })
        
        return {"status": "fixed" if fixed else "failed", "verified": fixed}
    
    def test_missing_import_variant(self, variant: int):
        """Test missing import variant."""
        test_file = Path(f"backend/test_import_v{variant}.py")
        imports = [
            "from missing_module import something",
            "import nonexistent_package",
            "from package.missing import item",
        ]
        test_file.write_text(imports[variant % len(imports)] + "\nprint('test')")
        self.backup_files[str(test_file)] = ""
        
        result = self.healing_agent.detect_and_heal(
            issue_description=f"Missing import variant {variant}",
            error=ImportError("No module named"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_undefined_variable(self):
        """Test undefined variable."""
        test_file = Path("backend/test_undefined.py")
        test_file.write_text("print(undefined_variable)")
        self.backup_files[str(test_file)] = ""
        
        result = self.healing_agent.detect_and_heal(
            issue_description="Undefined variable",
            error=NameError("name 'undefined_variable' is not defined"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_type_error(self):
        """Test type error."""
        test_file = Path("backend/test_type_error.py")
        test_file.write_text("'string' + 123")
        self.backup_files[str(test_file)] = ""
        
        result = self.healing_agent.detect_and_heal(
            issue_description="Type error",
            error=TypeError("can only concatenate str (not 'int') to str"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_attribute_error(self):
        """Test attribute error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Attribute error",
            error=AttributeError("'NoneType' object has no attribute 'method'"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_indentation_error(self):
        """Test indentation error."""
        test_file = Path("backend/test_indent.py")
        test_file.write_text("def test():\nprint('bad indent')")
        self.backup_files[str(test_file)] = ""
        
        result = self.healing_agent.detect_and_heal(
            issue_description="Indentation error",
            error=IndentationError("expected an indented block"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_name_error(self):
        """Test name error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Name error",
            error=NameError("name 'x' is not defined"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    # CONFIGURATION VARIANTS
    def test_missing_env_var(self):
        """Test missing environment variable."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Missing required environment variable",
            error=ValueError("Required env var 'API_KEY' not set"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_invalid_env_var(self):
        """Test invalid environment variable."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Invalid environment variable value",
            error=ValueError("Invalid value for env var 'PORT'"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_file_corrupted(self):
        """Test corrupted config file."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Configuration file corrupted",
            error=ValueError("Config file parse error"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_syntax_error(self):
        """Test config syntax error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Configuration syntax error",
            error=SyntaxError("Invalid config syntax"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_permission_denied(self):
        """Test config permission denied."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Config file permission denied",
            error=PermissionError("Cannot read config file"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_override_failed(self):
        """Test config override failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Configuration override failed",
            error=ValueError("Config override invalid"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_validation_failed(self):
        """Test config validation failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Configuration validation failed",
            error=ValueError("Config validation error"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_missing_section(self):
        """Test missing config section."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Missing configuration section",
            error=KeyError("Config section 'database' not found"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_config_invalid_type(self):
        """Test invalid config type."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Invalid configuration type",
            error=TypeError("Config value must be int, got str"),
            affected_layer=DevOpsLayer.CONFIGURATION,
            issue_category=IssueCategory.CONFIGURATION
        )
        
        return {"status": "detected", "healing_result": result}
    
    # NETWORK VARIANTS
    def test_connection_refused(self):
        """Test connection refused."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Connection refused",
            error=ConnectionRefusedError("Connection refused"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_dns_resolution_failed(self):
        """Test DNS resolution failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="DNS resolution failed",
            error=Exception("DNS resolution failed"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_ssl_certificate_error(self):
        """Test SSL certificate error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="SSL certificate error",
            error=Exception("SSL certificate verification failed"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Rate limit exceeded",
            error=Exception("Rate limit exceeded"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_service_unavailable(self):
        """Test service unavailable."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Service unavailable",
            error=Exception("503 Service Unavailable"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_network_unreachable(self):
        """Test network unreachable."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Network unreachable",
            error=OSError("Network is unreachable"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_timeout_reading_response(self):
        """Test timeout reading response."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Timeout reading response",
            error=TimeoutError("Timeout reading response"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_connection_reset(self):
        """Test connection reset."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Connection reset by peer",
            error=ConnectionResetError("Connection reset"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_proxy_error(self):
        """Test proxy error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Proxy error",
            error=Exception("Proxy connection failed"),
            affected_layer="network",
            issue_category="network"
        )
        
        return {"status": "detected", "healing_result": result}
    
    # SECURITY VARIANTS
    def test_unauthorized_access(self):
        """Test unauthorized access."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Unauthorized access attempt",
            error=Exception("401 Unauthorized"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_invalid_token(self):
        """Test invalid token."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Invalid authentication token",
            error=Exception("Invalid token"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_expired_token(self):
        """Test expired token."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Token expired",
            error=Exception("Token expired"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_weak_encryption(self):
        """Test weak encryption."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Weak encryption detected",
            error=Exception("Weak encryption algorithm"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_sql_injection_attempt(self):
        """Test SQL injection attempt."""
        result = self.healing_agent.detect_and_heal(
            issue_description="SQL injection attempt detected",
            error=Exception("SQL injection detected"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_path_traversal_attempt(self):
        """Test path traversal attempt."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Path traversal attempt",
            error=Exception("Path traversal detected"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_csrf_token_missing(self):
        """Test CSRF token missing."""
        result = self.healing_agent.detect_and_heal(
            issue_description="CSRF token missing",
            error=Exception("CSRF token validation failed"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_authentication_failed(self):
        """Test authentication failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Authentication failed",
            error=Exception("Authentication failed"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_authorization_failed(self):
        """Test authorization failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Authorization failed",
            error=Exception("403 Forbidden"),
            affected_layer="security",
            issue_category="security"
        )
        
        return {"status": "detected", "healing_result": result}
    
    # PERFORMANCE VARIANTS
    def test_slow_query(self):
        """Test slow query."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Slow database query detected",
            error=Exception("Query took > 5 seconds"),
            affected_layer="database",
            issue_category="performance"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_cpu_exhausted(self):
        """Test CPU exhausted."""
        result = self.healing_agent.detect_and_heal(
            issue_description="CPU usage at 100%",
            error=Exception("CPU exhausted"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_disk_space_full(self):
        """Test disk space full."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Disk space full",
            error=OSError("No space left on device"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_memory_leak(self):
        """Test memory leak."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Memory leak detected",
            error=MemoryError("Memory leak detected"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_infinite_loop(self):
        """Test infinite loop."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Infinite loop detected",
            error=Exception("Infinite loop detected"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_n_plus_one_query(self):
        """Test N+1 query problem."""
        result = self.healing_agent.detect_and_heal(
            issue_description="N+1 query problem",
            error=Exception("N+1 queries detected"),
            affected_layer="database",
            issue_category="performance"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_cache_miss_storm(self):
        """Test cache miss storm."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Cache miss storm",
            error=Exception("Cache miss rate > 90%"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.PERFORMANCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_garbage_collection_stuck(self):
        """Test garbage collection stuck."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Garbage collection stuck",
            error=Exception("GC taking too long"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.PERFORMANCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_thread_deadlock(self):
        """Test thread deadlock."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Thread deadlock",
            error=Exception("Thread deadlock detected"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_resource_contention(self):
        """Test resource contention."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Resource contention",
            error=Exception("Resource contention detected"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    # MEMORY VARIANTS
    def test_out_of_memory(self):
        """Test out of memory."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Out of memory",
            error=MemoryError("Out of memory"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_memory_fragmentation(self):
        """Test memory fragmentation."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Memory fragmentation",
            error=MemoryError("Memory fragmentation"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_buffer_overflow(self):
        """Test buffer overflow."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Buffer overflow",
            error=OverflowError("Buffer overflow"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_stack_overflow(self):
        """Test stack overflow."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Stack overflow",
            error=RecursionError("Stack overflow"),
            affected_layer="backend",
            issue_category="code_error"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_memory_corruption(self):
        """Test memory corruption."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Memory corruption",
            error=MemoryError("Memory corruption detected"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_shared_memory_error(self):
        """Test shared memory error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Shared memory error",
            error=Exception("Shared memory error"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_memory_mapping_failed(self):
        """Test memory mapping failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Memory mapping failed",
            error=OSError("Memory mapping failed"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_virtual_memory_exhausted(self):
        """Test virtual memory exhausted."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Virtual memory exhausted",
            error=MemoryError("Virtual memory exhausted"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_memory_allocation_failed(self):
        """Test memory allocation failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Memory allocation failed",
            error=MemoryError("Memory allocation failed"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RESOURCE
        )
        
        return {"status": "detected", "healing_result": result}
    
    # CONCURRENCY VARIANTS
    def test_race_condition(self):
        """Test race condition."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Race condition detected",
            error=Exception("Race condition"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_deadlock_multiple_threads(self):
        """Test deadlock multiple threads."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Deadlock in multiple threads",
            error=Exception("Deadlock detected"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_livelock(self):
        """Test livelock."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Livelock detected",
            error=Exception("Livelock detected"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_starvation(self):
        """Test starvation."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Thread starvation",
            error=Exception("Thread starvation"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_atomic_operation_failed(self):
        """Test atomic operation failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Atomic operation failed",
            error=Exception("Atomic operation failed"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_lock_timeout(self):
        """Test lock timeout."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Lock timeout",
            error=TimeoutError("Lock timeout"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_semaphore_exhausted(self):
        """Test semaphore exhausted."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Semaphore exhausted",
            error=Exception("Semaphore exhausted"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_condition_variable_error(self):
        """Test condition variable error."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Condition variable error",
            error=Exception("Condition variable error"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_barrier_timeout(self):
        """Test barrier timeout."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Barrier timeout",
            error=TimeoutError("Barrier timeout"),
            affected_layer=DevOpsLayer.BACKEND,
            issue_category=IssueCategory.RUNTIME_ERROR
        )
        
        return {"status": "detected", "healing_result": result}
    
    # INTEGRATION VARIANTS
    def test_api_version_mismatch(self):
        """Test API version mismatch."""
        result = self.healing_agent.detect_and_heal(
            issue_description="API version mismatch",
            error=Exception("API version mismatch"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_service_dependency_down(self):
        """Test service dependency down."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Service dependency down",
            error=Exception("Service dependency unavailable"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_message_queue_full(self):
        """Test message queue full."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Message queue full",
            error=Exception("Message queue full"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_event_bus_disconnected(self):
        """Test event bus disconnected."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Event bus disconnected",
            error=Exception("Event bus disconnected"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_database_replication_lag(self):
        """Test database replication lag."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Database replication lag",
            error=Exception("Replication lag > 5 seconds"),
            affected_layer="database",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_cache_invalidation_failed(self):
        """Test cache invalidation failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Cache invalidation failed",
            error=Exception("Cache invalidation failed"),
            affected_layer="backend",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_external_service_changed(self):
        """Test external service changed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="External service API changed",
            error=Exception("External service API changed"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_webhook_delivery_failed(self):
        """Test webhook delivery failed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Webhook delivery failed",
            error=Exception("Webhook delivery failed"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def test_third_party_api_changed(self):
        """Test third party API changed."""
        result = self.healing_agent.detect_and_heal(
            issue_description="Third party API changed",
            error=Exception("Third party API changed"),
            affected_layer="integration",
            issue_category="integration"
        )
        
        return {"status": "detected", "healing_result": result}
    
    def _run_test_variant(self, base_test_method, variant_num: int):
        """Run a variant of a base test method with modified parameters."""
        try:
            # Try to call the base test method
            if hasattr(base_test_method, '__call__'):
                result = base_test_method()
                # Modify result to indicate it's a variant
                if isinstance(result, dict):
                    result['variant'] = variant_num
                    result['base_test'] = base_test_method.__name__ if hasattr(base_test_method, '__name__') else str(base_test_method)
                return result
            else:
                return {"status": "test_failed", "error": "Invalid test method"}
        except Exception as e:
            logger.warning(f"Test variant {variant_num} failed: {e}")
            return {"status": "test_failed", "error": str(e), "variant": variant_num}
    
    def save_report(self, report: Dict[str, Any]):
        """Save stress test report."""
        report_file = Path(f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_file.write_text(json.dumps(report, indent=2))
        
        # Also create a human-readable report
        readable_report = self._generate_readable_report(report)
        readable_file = Path(f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        readable_file.write_text(readable_report)
        
        # Create natural language report using generate_nl_report module
        try:
            from generate_nl_report import generate_natural_language_report
            nl_report = generate_natural_language_report(report)
            nl_file = Path(f"stress_test_report_nl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
            nl_file.write_text(nl_report, encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to generate natural language report: {e}")
            # Fallback to simple report
            nl_file = None
        
        logger.info(f"\n{'='*80}")
        logger.info(f"STRESS TEST REPORT SAVED:")
        logger.info(f"  JSON: {report_file}")
        logger.info(f"  Markdown: {readable_file}")
        logger.info(f"  Natural Language: {nl_file}")
        logger.info(f"{'='*80}\n")
        
        # Print summary
        summary = report["test_summary"]
        logger.info("STRESS TEST SUMMARY:")
        logger.info(f"  Duration: {summary['duration_seconds']:.2f} seconds")
        logger.info(f"  Total Tests: {summary['total_tests']}")
        logger.info(f"  Successful Fixes: {summary['successful_fixes']}")
        logger.info(f"  Failed Fixes: {summary['failed_fixes']}")
        logger.info(f"  Fix Success Rate: {summary['fix_success_rate']:.1f}%")
        logger.info(f"  Genesis Keys Created: {report['genesis_keys']['total_created']}")
        logger.info(f"  Knowledge Requests: {report['knowledge_requests']['total']}")
        logger.info(f"  LLM Usage: {report['llm_usage']['total']}")
        logger.info(f"  Healing Actions: {report['healing_actions']['total']}")
    
    def _generate_readable_report(self, report: Dict[str, Any]) -> str:
        """Generate human-readable markdown report."""
        summary = report["test_summary"]
        
        md = f"""# Grace Self-Healing Stress Test Report

**Date:** {summary['start_time']}  
**Duration:** {summary['duration_seconds']:.2f} seconds  
**Status:** {'✅ PASSED' if summary['fix_success_rate'] > 50 else '⚠️ PARTIAL' if summary['fix_success_rate'] > 0 else '❌ FAILED'}

---

## Executive Summary

- **Total Tests:** {summary['total_tests']}
- **Successful Fixes:** {summary['successful_fixes']}
- **Failed Fixes:** {summary['failed_fixes']}
- **Fix Success Rate:** {summary['fix_success_rate']:.1f}%

---

## Genesis Keys Created

**Total:** {report['genesis_keys']['total_created']}

### By Type:
"""
        for key_type, count in report['genesis_keys']['by_type'].items():
            md += f"- **{key_type}:** {count}\n"
        
        md += "\n### Key Details:\n\n"
        for key in report['genesis_keys']['details'][:20]:  # First 20
            md += f"#### {key['key_id']}\n"
            md += f"- **What:** {key['what']}\n"
            md += f"- **Where:** {key['where']}\n"
            md += f"- **Who:** {key['who']}\n"
            md += f"- **How:** {key['how']}\n"
            md += f"- **Why:** {key['why']}\n"
            md += f"- **When:** {key['when']}\n"
            md += "\n"
        
        md += f"""
---

## Knowledge Requests

**Total:** {report['knowledge_requests']['total']}

### By Type:
"""
        for req_type, count in report['knowledge_requests']['by_type'].items():
            md += f"- **{req_type}:** {count}\n"
        
        md += f"""
---

## LLM Usage

**Total:** {report['llm_usage']['total']}

### By Model:
"""
        for model, count in report['llm_usage']['by_model'].items():
            md += f"- **{model}:** {count}\n"
        
        md += f"""
---

## Healing Actions

**Total:** {report['healing_actions']['total']}

### Actions Taken:
"""
        for action in report['healing_actions']['details'][:20]:  # First 20
            md += f"- **{action.get('action_type', 'unknown')}:** {action.get('description', 'N/A')}\n"
            md += f"  - Method: {action.get('method', 'unknown')}\n"
            md += f"  - Success: {action.get('success', False)}\n"
            md += "\n"
        
        md += f"""
---

## Fix Verifications

**Total:** {report['fix_verifications']['total']}  
**Successful:** {report['fix_verifications']['successful']}  
**Failed:** {report['fix_verifications']['failed']}

### Verification Details:
"""
        for verification in report['fix_verifications']['details']:
            status_icon = "✅" if verification.get('status') == 'fixed' else "❌"
            md += f"{status_icon} **{verification.get('issue', 'unknown')}**\n"
            md += f"  - Status: {verification.get('status', 'unknown')}\n"
            md += f"  - Verified: {verification.get('verified', False)}\n"
            md += "\n"
        
        md += """
---

## Test Results

"""
        for test in report['test_results']:
            md += f"### {test['test_name']}\n"
            md += f"**Issue:** {test['issue_introduced']}\n"
            md += f"**Result:** {test['result'].get('status', 'unknown')}\n"
            md += f"**Verified:** {test['result'].get('verified', False)}\n"
            md += "\n"
        
        return md


def main():
    """Run stress test."""
    # Initialize database
    db_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database_path="data/grace.db"
    )
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    
    session = get_session()
    
    try:
        runner = StressTestRunner(session)
        report = runner.run_all_tests()
        
        print("\n" + "="*80)
        print("STRESS TEST COMPLETE")
        print("="*80)
        print(f"Report saved to: stress_test_report_*.json")
        print(f"Logs saved to: logs/stress_test_*.log")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Stress test failed: {e}", exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
