import sys
import os
from pathlib import Path
import asyncio
import logging
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
from sqlalchemy.orm import Session
import threading
class AggressiveStressTester:
    logger = logging.getLogger(__name__)
    """Aggressive stress testing designed to break Grace."""
    
    def __init__(self, session: Session, knowledge_base_path: Path):
        self.session = session
        self.kb_path = knowledge_base_path
        self.test_results: List[Dict[str, Any]] = []
        self.issues_found: List[Dict[str, Any]] = []
        self.test_duration_minutes = 60  # Run for 60 minutes by default
        self.concurrent_workers = 50  # Aggressive concurrency
        
    def log_test_result(
        self,
        test_name: str,
        perspective: str,
        passed: bool,
        duration_ms: float,
        metrics: Dict[str, Any],
        errors: List[str],
        warnings: List[str]
    ):
        """Log test result."""
        result = {
            "test_name": test_name,
            "perspective": perspective,
            "passed": passed,
            "duration_ms": duration_ms,
            "metrics": metrics,
            "errors": errors,
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat(),
            "aggressive": True
        }
        
        self.test_results.append(result)
        
        # Save to log file
        if TEST_LOG_PATH.exists():
            with open(TEST_LOG_PATH, 'r') as f:
                all_results = json.load(f)
        else:
            all_results = []
        
        all_results.append(result)
        
        with open(TEST_LOG_PATH, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        if not passed or errors:
            self.issues_found.append(result)
            logger.error(f"[AGGRESSIVE-TEST] 💥 {test_name} ({perspective}): BROKEN")
            if errors:
                logger.error(f"  Errors: {errors[:3]}...")  # Show first 3
        else:
            logger.info(f"[AGGRESSIVE-TEST] ✅ {test_name} ({perspective}): SURVIVED ({duration_ms:.1f}ms)")
    
    # ==================== AGGRESSIVE TEST 1: Memory Bomb ====================
    
    def test_memory_bomb(self) -> Dict[str, Any]:
        """Bombard memory system with massive volume."""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            if self.session is None:
                errors.append("Database session not available")
                raise Exception("Database session required")
            
            if get_memory_analytics is None:
                logger.warning("Memory analytics not available - skipping test")
                return {"passed": True, "errors": [], "metrics": {"skipped": True, "reason": "Module not available"}}
            
            # Aggressive: 1000 operations in parallel
            operations_completed = 0
            operations_failed = 0
            
            def memory_operation(op_id: int):
                try:
                    analytics = get_memory_analytics(self.session, self.kb_path)
                    dashboard = analytics.get_comprehensive_dashboard()
                    return {"success": True, "op_id": op_id}
                except Exception as e:
                    return {"success": False, "op_id": op_id, "error": str(e)}
            
            with ThreadPoolExecutor(max_workers=self.concurrent_workers) as executor:
                futures = [executor.submit(memory_operation, i) for i in range(1000)]
                for future in as_completed(futures):
                    result = future.result()
                    if result.get("success"):
                        operations_completed += 1
                    else:
                        operations_failed += 1
                        errors.append(f"Operation {result.get('op_id')} failed: {result.get('error')}")
            
            metrics["operations_completed"] = operations_completed
            metrics["operations_failed"] = operations_failed
            metrics["success_rate"] = operations_completed / 1000 if operations_completed > 0 else 0.0
            
            if metrics["success_rate"] < 0.95:
                errors.append(f"Success rate too low: {metrics['success_rate']:.2%}")
            
        except Exception as e:
            errors.append(f"Memory bomb test failed: {str(e)}")
            errors.append(traceback.format_exc())
        
        duration_ms = (time.time() - start_time) * 1000
        
        self.log_test_result(
            "Memory Bomb",
            "Massive Volume Attack",
            len(errors) == 0,
            duration_ms,
            metrics,
            errors,
            warnings
        )
        
        return {"passed": len(errors) == 0, "errors": errors, "metrics": metrics}
    
    # ==================== AGGRESSIVE TEST 2: Concurrent Chaos ====================
    
    def test_concurrent_chaos(self) -> Dict[str, Any]:
        """Chaotic concurrent access from all directions."""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            if self.session is None:
                # Try to initialize session if not available
                if get_session is not None:
                    try:
                        from backend.database.config import DatabaseConfig
                        from backend.database.connection import DatabaseConnection
                        from backend.database.session import initialize_session_factory
                        
                        # Initialize database if not already done
                        try:
                            DatabaseConnection.get_engine()
                        except RuntimeError:
                            # Database not initialized, initialize it
                            db_config = DatabaseConfig()
                            DatabaseConnection.initialize(db_config)
                        
                        initialize_session_factory()
                        self.session = next(get_session())
                        logger.info("Database session initialized during test")
                    except Exception as e:
                        errors.append(f"Database session not available: {e}")
                        raise Exception("Database session required")
                else:
                    errors.append("Database session not available")
                    raise Exception("Database session required")
            
            # Aggressive: 2000 concurrent operations with random delays
            operations = []
            
            def chaotic_operation(op_id: int):
                try:
                    # Random delay to create chaos
                    time.sleep(random.uniform(0.001, 0.1))
                    
                    if get_memory_analytics is not None:
                        analytics = get_memory_analytics(self.session, self.kb_path)
                        dashboard = analytics.get_comprehensive_dashboard()
                    
                    if get_enterprise_librarian is not None:
                        librarian = get_enterprise_librarian(self.session, self.kb_path)
                        priorities = librarian.prioritize_documents()
                    
                    return {"success": True, "op_id": op_id}
                except Exception as e:
                    return {"success": False, "op_id": op_id, "error": str(e)}
            
            with ThreadPoolExecutor(max_workers=self.concurrent_workers) as executor:
                futures = [executor.submit(chaotic_operation, i) for i in range(2000)]
                for future in as_completed(futures):
                    result = future.result()
                    operations.append(result)
            
            successful = sum(1 for op in operations if op.get("success"))
            metrics["total_operations"] = len(operations)
            metrics["successful"] = successful
            metrics["success_rate"] = successful / len(operations) if operations else 0.0
            
            if metrics["success_rate"] < 0.90:
                errors.append(f"Concurrent chaos success rate too low: {metrics['success_rate']:.2%}")
            
        except Exception as e:
            errors.append(f"Concurrent chaos test failed: {str(e)}")
            errors.append(traceback.format_exc())
        
        duration_ms = (time.time() - start_time) * 1000
        
        self.log_test_result(
            "Concurrent Chaos",
            "Multi-Directional Attack",
            len(errors) == 0,
            duration_ms,
            metrics,
            errors,
            warnings
        )
        
        return {"passed": len(errors) == 0, "errors": errors, "metrics": metrics}
    
    # ==================== AGGRESSIVE TEST 3: Resource Exhaustion ====================
    
    def test_resource_exhaustion(self) -> Dict[str, Any]:
        """Try to exhaust all resources."""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # Baseline
            baseline_memory = process.memory_info().rss / 1024 / 1024
            baseline_cpu = process.cpu_percent(interval=1)
            
            # Aggressive: Create many objects and hold them
            objects_created = []
            for i in range(10000):
                obj = {
                    "id": i,
                    "data": "x" * 1000,  # 1KB per object
                    "timestamp": datetime.utcnow().isoformat()
                }
                objects_created.append(obj)
                
                # Check memory every 1000 objects
                if i % 1000 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    if current_memory > baseline_memory * 2:
                        warnings.append(f"Memory doubled at {i} objects: {current_memory:.1f} MB")
            
            # Final measurements
            final_memory = process.memory_info().rss / 1024 / 1024
            final_cpu = process.cpu_percent(interval=1)
            
            metrics["baseline_memory_mb"] = baseline_memory
            metrics["final_memory_mb"] = final_memory
            metrics["memory_increase_mb"] = final_memory - baseline_memory
            metrics["baseline_cpu"] = baseline_cpu
            metrics["final_cpu"] = final_cpu
            metrics["objects_created"] = len(objects_created)
            
            # Cleanup
            del objects_created
            
            if final_memory > baseline_memory * 3:
                errors.append(f"Memory leak detected: {final_memory:.1f} MB (baseline: {baseline_memory:.1f} MB)")
            
        except ImportError:
            warnings.append("psutil not available - cannot measure resource exhaustion")
        except Exception as e:
            errors.append(f"Resource exhaustion test failed: {str(e)}")
            errors.append(traceback.format_exc())
        
        duration_ms = (time.time() - start_time) * 1000
        
        self.log_test_result(
            "Resource Exhaustion",
            "Memory/CPU Stress",
            len(errors) == 0,
            duration_ms,
            metrics,
            errors,
            warnings
        )
        
        return {"passed": len(errors) == 0, "errors": errors, "metrics": metrics}
    
    # ==================== AGGRESSIVE TEST 4: Rapid Fire Requests ====================
    
    def test_rapid_fire_requests(self) -> Dict[str, Any]:
        """Rapid fire requests with no delay."""
        start_time = time.time()
        errors = []
        warnings = []
        metrics = {}
        
        try:
            if self.session is None:
                # Try to initialize session if not available
                if get_session is not None:
                    try:
                        from backend.database.config import DatabaseConfig
                        from backend.database.connection import DatabaseConnection
                        from backend.database.session import initialize_session_factory
                        
                        # Initialize database if not already done
                        try:
                            DatabaseConnection.get_engine()
                        except RuntimeError:
                            # Database not initialized, initialize it
                            db_config = DatabaseConfig()
                            DatabaseConnection.initialize(db_config)
                        
                        initialize_session_factory()
                        self.session = next(get_session())
                        logger.info("Database session initialized during test")
                    except Exception as e:
                        errors.append(f"Database session not available: {e}")
                        raise Exception("Database session required")
                else:
                    errors.append("Database session not available")
                    raise Exception("Database session required")
            
            # Aggressive: 5000 rapid requests
            requests_sent = 0
            requests_succeeded = 0
            requests_failed = 0
            
            def rapid_request(req_id: int):
                try:
                    if get_memory_analytics is not None:
                        analytics = get_memory_analytics(self.session, self.kb_path)
                        dashboard = analytics.get_comprehensive_dashboard()
                    return {"success": True, "req_id": req_id}
                except Exception as e:
                    return {"success": False, "req_id": req_id, "error": str(e)}
            
            # Send all requests as fast as possible
            with ThreadPoolExecutor(max_workers=self.concurrent_workers) as executor:
                futures = [executor.submit(rapid_request, i) for i in range(5000)]
                for future in as_completed(futures):
                    requests_sent += 1
                    result = future.result()
                    if result.get("success"):
                        requests_succeeded += 1
                    else:
                        requests_failed += 1
                        if requests_failed <= 10:  # Log first 10 failures
                            errors.append(f"Request {result.get('req_id')} failed: {result.get('error')}")
            
            metrics["requests_sent"] = requests_sent
            metrics["requests_succeeded"] = requests_succeeded
            metrics["requests_failed"] = requests_failed
            metrics["success_rate"] = requests_succeeded / requests_sent if requests_sent > 0 else 0.0
            metrics["requests_per_second"] = requests_sent / ((time.time() - start_time) or 0.001)
            
            if metrics["success_rate"] < 0.80:
                errors.append(f"Rapid fire success rate too low: {metrics['success_rate']:.2%}")
            
        except Exception as e:
            errors.append(f"Rapid fire test failed: {str(e)}")
            errors.append(traceback.format_exc())
        
        duration_ms = (time.time() - start_time) * 1000
        
        self.log_test_result(
            "Rapid Fire Requests",
            "No-Delay Attack",
            len(errors) == 0,
            duration_ms,
            metrics,
            errors,
            warnings
        )
        
        return {"passed": len(errors) == 0, "errors": errors, "metrics": metrics}
    
    # ==================== AGGRESSIVE TEST 5: Long Duration Stress ====================
    
    def test_long_duration_stress(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Run stress tests for extended duration."""
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        errors = []
        warnings = []
        metrics = {}
        
        try:
            if self.session is None:
                # Try to initialize session if not available
                if get_session is not None:
                    try:
                        from backend.database.config import DatabaseConfig
                        from backend.database.connection import DatabaseConnection
                        from backend.database.session import initialize_session_factory
                        
                        # Initialize database if not already done
                        try:
                            DatabaseConnection.get_engine()
                        except RuntimeError:
                            # Database not initialized, initialize it
                            db_config = DatabaseConfig()
                            DatabaseConnection.initialize(db_config)
                        
                        initialize_session_factory()
                        self.session = next(get_session())
                        logger.info("Database session initialized during test")
                    except Exception as e:
                        errors.append(f"Database session not available: {e}")
                        raise Exception("Database session required")
                else:
                    errors.append("Database session not available")
                    raise Exception("Database session required")
            
            cycles_completed = 0
            cycles_failed = 0
            total_operations = 0
            
            logger.info(f"[AGGRESSIVE-TEST] Starting long duration stress test for {duration_minutes} minutes...")
            
            while time.time() < end_time:
                cycle_start = time.time()
                cycles_completed += 1
                
                # Run a cycle of operations
                try:
                    if get_memory_analytics is not None:
                        analytics = get_memory_analytics(self.session, self.kb_path)
                        dashboard = analytics.get_comprehensive_dashboard()
                        total_operations += 1
                    
                    if get_enterprise_librarian is not None:
                        librarian = get_enterprise_librarian(self.session, self.kb_path)
                        priorities = librarian.prioritize_documents()
                        total_operations += 1
                    
                    # Small delay to prevent complete CPU lock
                    time.sleep(0.1)
                    
                except Exception as e:
                    cycles_failed += 1
                    if cycles_failed <= 5:  # Log first 5 failures
                        errors.append(f"Cycle {cycles_completed} failed: {str(e)}")
                
                # Log progress every 5 minutes
                elapsed_minutes = (time.time() - start_time) / 60
                if cycles_completed % 300 == 0:  # Every 5 minutes at 1 cycle/second
                    logger.info(f"[AGGRESSIVE-TEST] Long duration: {elapsed_minutes:.1f} minutes, {cycles_completed} cycles, {total_operations} operations")
            
            metrics["duration_minutes"] = duration_minutes
            metrics["cycles_completed"] = cycles_completed
            metrics["cycles_failed"] = cycles_failed
            metrics["total_operations"] = total_operations
            metrics["success_rate"] = (cycles_completed - cycles_failed) / cycles_completed if cycles_completed > 0 else 0.0
            
            if metrics["success_rate"] < 0.95:
                errors.append(f"Long duration success rate too low: {metrics['success_rate']:.2%}")
            
        except Exception as e:
            errors.append(f"Long duration stress test failed: {str(e)}")
            errors.append(traceback.format_exc())
        
        duration_ms = (time.time() - start_time) * 1000
        
        self.log_test_result(
            "Long Duration Stress",
            f"{duration_minutes} Minute Endurance",
            len(errors) == 0,
            duration_ms,
            metrics,
            errors,
            warnings
        )
        
        return {"passed": len(errors) == 0, "errors": errors, "metrics": metrics}
    
    # ==================== RUN ALL AGGRESSIVE TESTS ====================
    
    def run_all_aggressive_tests(self, long_duration_minutes: int = 60) -> Dict[str, Any]:
        """Run all aggressive stress tests."""
        logger.info("[AGGRESSIVE-TEST] 💥 Starting aggressive stress tests to BREAK Grace...")
        logger.info(f"[AGGRESSIVE-TEST] Duration: {long_duration_minutes} minutes")
        logger.info(f"[AGGRESSIVE-TEST] Concurrent workers: {self.concurrent_workers}")
        
        test_methods = [
            ("Memory Bomb", self.test_memory_bomb),
            ("Concurrent Chaos", self.test_concurrent_chaos),
            ("Resource Exhaustion", self.test_resource_exhaustion),
            ("Rapid Fire Requests", self.test_rapid_fire_requests),
            ("Long Duration Stress", lambda: self.test_long_duration_stress(long_duration_minutes))
        ]
        
        results = {}
        for test_name, test_method in test_methods:
            try:
                logger.info(f"[AGGRESSIVE-TEST] Running {test_name}...")
                result = test_method()
                results[test_name] = result
            except Exception as e:
                logger.error(f"[AGGRESSIVE-TEST] Test {test_name} crashed: {e}")
                results[test_name] = {"passed": False, "errors": [str(e)], "metrics": {}}
        
        # Summary
        total_tests = len(test_methods)
        passed_tests = sum(1 for r in results.values() if r.get("passed", False))
        failed_tests = total_tests - passed_tests
        
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0.0,
            "issues_found": len(self.issues_found),
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
            "aggressive": True
        }
        
        logger.info(
            f"[AGGRESSIVE-TEST] 💥 Complete: {passed_tests}/{total_tests} survived, "
            f"{len(self.issues_found)} breaking points found"
        )
        
        return summary


# Import with error handling
try:
    from backend.database.session import get_session
except ImportError:
    get_session = None

try:
    from backend.cognitive.memory_analytics import get_memory_analytics
except ImportError as e:
    logger.warning(f"Could not import memory_analytics: {e}")
    # Try alternative import path
    try:
        import sys
        import importlib.util
        analytics_path = project_root / "backend" / "cognitive" / "memory_analytics.py"
        if analytics_path.exists():
            spec = importlib.util.spec_from_file_location(
                "memory_analytics", str(analytics_path)
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Add to sys.modules so it can be imported
                sys.modules["backend.cognitive.memory_analytics"] = module
                spec.loader.exec_module(module)
                get_memory_analytics = getattr(module, "get_memory_analytics", None)
                logger.info("Loaded memory_analytics via direct file import")
            else:
                get_memory_analytics = None
        else:
            get_memory_analytics = None
    except Exception as e2:
        logger.warning(f"Alternative import also failed: {e2}")
        get_memory_analytics = None

try:
    from backend.cognitive.memory_lifecycle_manager import get_memory_lifecycle_manager
except ImportError:
    get_memory_lifecycle_manager = None

try:
    from backend.librarian.enterprise_librarian import get_enterprise_librarian
except ImportError:
    get_enterprise_librarian = None

try:
    from backend.world_model.enterprise_world_model import get_enterprise_world_model
except ImportError:
    get_enterprise_world_model = None

try:
    from backend.layer1.enterprise_connectors import get_enterprise_layer1_connectors
except ImportError:
    get_enterprise_layer1_connectors = None


def run_aggressive_stress_tests(duration_minutes: int = 60):
    """Main function to run aggressive stress tests."""
    session = None
    kb_path = Path("backend/knowledge_base")
    
    # Try to get session with proper initialization
    try:
        from backend.database.config import DatabaseConfig
        from backend.database.connection import DatabaseConnection
        from backend.database.session import initialize_session_factory
        
        # Initialize database connection
        logger.info("Initializing database connection...")
        try:
            db_config = DatabaseConfig.from_env()  # Use environment or defaults
        except:
            # Fallback to default config if from_env fails
            db_config = DatabaseConfig()
        
        DatabaseConnection.initialize(db_config)
        logger.info("✅ Database connection initialized")
        
        # Initialize session factory
        initialize_session_factory()
        logger.info("✅ Session factory initialized")
        
        # Create tables if needed (skip if models not available)
        try:
            from backend.database.migration import create_tables
            create_tables()
            logger.info("✅ Database tables verified")
        except ImportError as e:
            logger.warning(f"Could not import migration module (models may not be available): {e}")
        except Exception as e:
            logger.warning(f"Table creation warning: {e}")
        
        # Get session
        session = next(get_session())
        logger.info("✅ Database session created for aggressive testing")
        
        # Test the session with a simple query
        try:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            session.commit()
            logger.info("✅ Database connection verified")
        except Exception as e:
            logger.warning(f"Database connection test failed: {e}")
            try:
                session.rollback()
            except:
                pass
            session = None
                
    except ImportError as e:
        logger.warning(f"Could not import database modules: {e}")
        logger.warning("Tests will run without database (some tests will be skipped)")
        session = None
    except Exception as e:
        logger.warning(f"Could not initialize database session: {e}")
        logger.warning(f"Error details: {traceback.format_exc()}")
        logger.warning("Tests will run without database (some tests will be skipped)")
        session = None
    
    # Run aggressive tests
    tester = AggressiveStressTester(session, kb_path)
    summary = tester.run_all_aggressive_tests(duration_minutes)
    
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    summary = run_aggressive_stress_tests(60)
    print(json.dumps(summary, indent=2, default=str))
