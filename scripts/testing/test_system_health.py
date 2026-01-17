#!/usr/bin/env python3
"""
System Health Check Test
Validates that all Grace services are running and healthy.
"""

import sys
import os
import json
import logging
import time
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
import traceback

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class SystemHealthChecker:
    """Checks health of all Grace system components."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {
            "start_time": datetime.now(UTC).isoformat(),
            "checks": [],
            "overall_status": "unknown",
            "services_healthy": 0,
            "services_total": 0
        }
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connection and health."""
        logger.info("[HEALTH] Checking database...")
        
        try:
            from database.connection import DatabaseConnection
            from database.config import DatabaseConfig, DatabaseType
            from database.session import initialize_session_factory
            from sqlalchemy import text
            
            # Initialize if needed
            try:
                engine = DatabaseConnection.get_engine()
            except RuntimeError:
                # Not initialized, initialize it
                db_config = DatabaseConfig(
                    db_type=DatabaseType.SQLITE,
                    database_path="data/grace.db"
                )
                DatabaseConnection.initialize(db_config)
                engine = DatabaseConnection.get_engine()
            
            # Test connection
            session_factory = initialize_session_factory()
            session = session_factory()
            
            try:
                result = session.execute(text("SELECT 1"))
                result.fetchone()
                
                # Check database file exists
                db_path = Path("data/grace.db")
                db_exists = db_path.exists()
                db_size = db_path.stat().st_size if db_exists else 0
                
                return {
                    "status": "healthy",
                    "connected": True,
                    "database_exists": db_exists,
                    "database_size_mb": round(db_size / 1024 / 1024, 2),
                    "test_query": "passed"
                }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"[HEALTH] Database check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    def check_file_system(self) -> Dict[str, Any]:
        """Check file system access and permissions."""
        logger.info("[HEALTH] Checking file system...")
        
        try:
            # Check key directories exist
            dirs_to_check = [
                "backend",
                "data",
                "knowledge_base",
                "logs",
                "backend/cognitive",
                "backend/database",
                "backend/api"
            ]
            
            dirs_status = {}
            for dir_path in dirs_to_check:
                path = Path(dir_path)
                dirs_status[dir_path] = {
                    "exists": path.exists(),
                    "readable": os.access(path, os.R_OK) if path.exists() else False,
                    "writable": os.access(path, os.W_OK) if path.exists() else False
                }
            
            # Test file write
            test_file = Path("data/.health_check_test")
            try:
                test_file.write_text("test", encoding='utf-8')
                test_write = True
                test_file.unlink()
            except Exception as e:
                test_write = False
                write_error = str(e)
            
            all_accessible = all(
                d["exists"] and d["readable"] 
                for d in dirs_status.values()
            )
            
            return {
                "status": "healthy" if all_accessible and test_write else "degraded",
                "directories": dirs_status,
                "test_write": test_write,
                "write_error": write_error if not test_write else None
            }
            
        except Exception as e:
            logger.error(f"[HEALTH] File system check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_memory_resources(self) -> Dict[str, Any]:
        """Check available memory and resources."""
        logger.info("[HEALTH] Checking memory resources...")
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            memory_mb = memory_info.rss / 1024 / 1024
            available_mb = system_memory.available / 1024 / 1024
            total_mb = system_memory.total / 1024 / 1024
            memory_percent = system_memory.percent
            
            # Check CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Health thresholds
            memory_healthy = available_mb > 512  # At least 512MB available
            cpu_healthy = cpu_percent < 90  # CPU under 90%
            
            return {
                "status": "healthy" if (memory_healthy and cpu_healthy) else "degraded",
                "process_memory_mb": round(memory_mb, 2),
                "available_memory_mb": round(available_mb, 2),
                "total_memory_mb": round(total_mb, 2),
                "memory_usage_percent": round(memory_percent, 2),
                "cpu_usage_percent": round(cpu_percent, 2),
                "memory_healthy": memory_healthy,
                "cpu_healthy": cpu_healthy
            }
            
        except ImportError:
            logger.warning("[HEALTH] psutil not available, skipping detailed memory check")
            return {
                "status": "unknown",
                "message": "psutil not installed for detailed memory monitoring"
            }
        except Exception as e:
            logger.error(f"[HEALTH] Memory check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_vector_database(self) -> Dict[str, Any]:
        """Check Qdrant vector database connection."""
        logger.info("[HEALTH] Checking vector database (Qdrant)...")
        
        try:
            from vector_db.client import QdrantClient
            
            client = QdrantClient()
            
            # Try to connect
            try:
                collections = client.list_collections()
                connected = True
                collection_count = len(collections) if collections else 0
            except Exception as e:
                connected = False
                error_msg = str(e)
            
            if connected:
                return {
                    "status": "healthy",
                    "connected": True,
                    "collections": collection_count
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": error_msg if 'error_msg' in locals() else "Connection failed",
                    "note": "Qdrant may not be running. Install with: docker run -p 6333:6333 qdrant/qdrant"
                }
                
        except ImportError as e:
            logger.warning(f"[HEALTH] Vector DB client not available: {e}")
            return {
                "status": "unknown",
                "message": "Vector database client not available"
            }
        except Exception as e:
            logger.error(f"[HEALTH] Vector database check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    def check_llm_services(self) -> Dict[str, Any]:
        """Check LLM services (Ollama) availability."""
        logger.info("[HEALTH] Checking LLM services (Ollama)...")
        
        try:
            from llm_orchestrator.multi_llm_client import MultiLLMClient
            
            client = MultiLLMClient()
            
            # Try to discover models
            try:
                models = client.discover_available_models()
                available = len(models) > 0
                model_count = len(models)
                model_names = [m.get('name', 'unknown') for m in models[:5]]  # First 5
            except Exception as e:
                available = False
                model_count = 0
                model_names = []
                error_msg = str(e)
            
            if available:
                return {
                    "status": "healthy",
                    "connected": True,
                    "models_available": model_count,
                    "model_names": model_names
                }
            else:
                return {
                    "status": "degraded",
                    "connected": False,
                    "models_available": 0,
                    "error": error_msg if 'error_msg' in locals() else "No models available",
                    "note": "Ollama may not be running. Start with: ollama serve"
                }
                
        except ImportError as e:
            logger.warning(f"[HEALTH] LLM client not available: {e}")
            return {
                "status": "unknown",
                "message": "LLM client not available"
            }
        except Exception as e:
            logger.error(f"[HEALTH] LLM services check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    def check_api_endpoints(self) -> Dict[str, Any]:
        """Check if API endpoints are accessible (if server is running)."""
        logger.info("[HEALTH] Checking API endpoints...")
        
        try:
            import requests
            
            base_url = "http://localhost:8000"
            endpoints_to_check = [
                "/health",
                "/grace/health",
                "/grace/status"
            ]
            
            endpoint_status = {}
            server_running = False
            
            for endpoint in endpoints_to_check:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=2)
                    endpoint_status[endpoint] = {
                        "status_code": response.status_code,
                        "accessible": response.status_code < 500,
                        "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
                    }
                    server_running = True
                except requests.exceptions.RequestException as e:
                    endpoint_status[endpoint] = {
                        "accessible": False,
                        "error": str(e)
                    }
            
            if server_running:
                return {
                    "status": "healthy",
                    "server_running": True,
                    "base_url": base_url,
                    "endpoints": endpoint_status
                }
            else:
                return {
                    "status": "degraded",
                    "server_running": False,
                    "note": "FastAPI server may not be running. Start with: python backend/app.py",
                    "endpoints": endpoint_status
                }
                
        except ImportError:
            logger.warning("[HEALTH] requests library not available, skipping API check")
            return {
                "status": "unknown",
                "message": "requests library not installed for API checks"
            }
        except Exception as e:
            logger.error(f"[HEALTH] API endpoints check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_core_modules(self) -> Dict[str, Any]:
        """Check if core Python modules can be imported."""
        logger.info("[HEALTH] Checking core modules...")
        
        modules_to_check = [
            "cognitive.autonomous_healing_system",
            "database.session",
            "diagnostic_machine.automatic_bug_fixer",
            "genesis.genesis_key_service",
            "genesis.symbiotic_version_control",
            "cognitive.memory_mesh_integration",
            "cognitive.learning_memory",
            "layer1.message_bus",
            "api.file_ingestion",
            "llm_orchestrator.multi_llm_client"
        ]
        
        module_status = {}
        
        for module_name in modules_to_check:
            try:
                __import__(module_name)
                module_status[module_name] = {
                    "importable": True,
                    "status": "ok"
                }
            except Exception as e:
                module_status[module_name] = {
                    "importable": False,
                    "status": "error",
                    "error": str(e)
                }
        
        all_importable = all(m["importable"] for m in module_status.values())
        
        return {
            "status": "healthy" if all_importable else "degraded",
            "modules": module_status,
            "all_importable": all_importable,
            "modules_checked": len(modules_to_check),
            "modules_ok": sum(1 for m in module_status.values() if m["importable"])
        }
    
    def check_ingestion_system(self) -> Dict[str, Any]:
        """Check file ingestion system."""
        logger.info("[HEALTH] Checking file ingestion system...")
        
        try:
            from pathlib import Path
            
            # Check knowledge_base directory exists
            kb_path = Path("knowledge_base")
            kb_exists = kb_path.exists()
            
            # Check ingestion API is available
            try:
                from api.file_ingestion import router
                api_available = True
            except ImportError:
                api_available = False
            
            # Check ingestion directories
            ingestion_dirs = {
                "knowledge_base": kb_path.exists(),
                "knowledge_base/layer_1": (kb_path / "layer_1").exists() if kb_path.exists() else False,
                "knowledge_base/exports": (kb_path / "exports").exists() if kb_path.exists() else False
            }
            
            if api_available and kb_exists:
                return {
                    "status": "healthy",
                    "api_available": True,
                    "knowledge_base_exists": kb_exists,
                    "directories": ingestion_dirs
                }
            else:
                return {
                    "status": "degraded",
                    "api_available": api_available,
                    "knowledge_base_exists": kb_exists,
                    "directories": ingestion_dirs
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_genesis_system(self) -> Dict[str, Any]:
        """Check Genesis key tracking system."""
        logger.info("[HEALTH] Checking Genesis key system...")
        
        try:
            from genesis.genesis_key_service import get_genesis_service
            from database.session import initialize_session_factory
            from database.connection import DatabaseConnection
            
            # Get session
            session_factory = initialize_session_factory()
            session = session_factory()
            
            try:
                # Try to get genesis service
                genesis_service = get_genesis_service(session=session)
                
                # Check if we can create a test key
                try:
                    from models.genesis_key_models import GenesisKeyType
                    # Use a valid GenesisKeyType value
                    # Valid values include: FILE_OPERATION, API_REQUEST, etc.
                    test_key = genesis_service.create_key(
                        key_type=GenesisKeyType.FILE_OPERATION,
                        what_description="Health check test",
                        who_actor="system",
                        why_reason="Health validation",
                        how_method="system_check"
                    )
                    can_create = True
                    test_key_id = test_key.key_id if hasattr(test_key, 'key_id') else "created"
                except Exception as e:
                    can_create = False
                    create_error = str(e)
                    test_key_id = None
                
                return {
                    "status": "healthy" if can_create else "degraded",
                    "service_available": True,
                    "can_create_keys": can_create,
                    "test_key_id": test_key_id,
                    "create_error": create_error if not can_create else None
                }
            finally:
                session.close()
                
        except ImportError as e:
            return {
                "status": "degraded",
                "error": f"Import error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_self_healing_system(self) -> Dict[str, Any]:
        """Check self-healing system."""
        logger.info("[HEALTH] Checking self-healing system...")
        
        try:
            from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
            from database.session import initialize_session_factory
            from database.connection import DatabaseConnection
            
            # Get session
            session_factory = initialize_session_factory()
            session = session_factory()
            
            try:
                # Try to initialize healing system
                healing_system = get_autonomous_healing(
                    session=session,
                    repo_path=Path("backend"),
                    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                    enable_learning=True
                )
                
                # Try health assessment
                try:
                    assessment = healing_system.assess_system_health()
                    can_assess = True
                    health_status = assessment.get("health_status", "unknown")
                except Exception as e:
                    can_assess = False
                    assess_error = str(e)
                    health_status = None
                
                return {
                    "status": "healthy" if can_assess else "degraded",
                    "system_initialized": True,
                    "can_assess_health": can_assess,
                    "health_status": health_status,
                    "assess_error": assess_error if not can_assess else None
                }
            finally:
                session.close()
                
        except ImportError as e:
            return {
                "status": "degraded",
                "error": f"Import error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_diagnostic_system(self) -> Dict[str, Any]:
        """Check diagnostic machine and bug fixer."""
        logger.info("[HEALTH] Checking diagnostic system...")
        
        try:
            from diagnostic_machine.automatic_bug_fixer import AutomaticBugFixer
            from diagnostic_machine.proactive_code_scanner import ProactiveCodeScanner
            from pathlib import Path
            
            # Check scanner
            try:
                scanner = ProactiveCodeScanner(backend_dir=Path("backend"))
                scanner_ok = True
            except Exception as e:
                scanner_ok = False
                scanner_error = str(e)
            
            # Check fixer
            try:
                fixer = AutomaticBugFixer(backend_dir=Path("backend"))
                fixer_ok = True
            except Exception as e:
                fixer_ok = False
                fixer_error = str(e)
            
            if scanner_ok and fixer_ok:
                return {
                    "status": "healthy",
                    "scanner_available": True,
                    "fixer_available": True
                }
            else:
                return {
                    "status": "degraded",
                    "scanner_available": scanner_ok,
                    "scanner_error": scanner_error if not scanner_ok else None,
                    "fixer_available": fixer_ok,
                    "fixer_error": fixer_error if not fixer_ok else None
                }
                
        except ImportError as e:
            return {
                "status": "degraded",
                "error": f"Import error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_layer1_system(self) -> Dict[str, Any]:
        """Check Layer 1 autonomous system."""
        logger.info("[HEALTH] Checking Layer 1 system...")
        
        try:
            from layer1.message_bus import get_message_bus
            
            # Check message bus
            try:
                message_bus = get_message_bus()
                bus_ok = True
                
                # Check if message bus has components registered
                try:
                    components = getattr(message_bus, '_components', {})
                    component_count = len(components) if components else 0
                except:
                    component_count = 0
                
            except Exception as e:
                bus_ok = False
                bus_error = str(e)
                component_count = 0
            
            if bus_ok:
                return {
                    "status": "healthy",
                    "message_bus_available": True,
                    "components_registered": component_count
                }
            else:
                return {
                    "status": "degraded",
                    "message_bus_available": False,
                    "message_bus_error": bus_error if 'bus_error' in locals() else "Unknown error"
                }
                
        except ImportError as e:
            return {
                "status": "degraded",
                "error": f"Import error: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_knowledge_base(self) -> Dict[str, Any]:
        """Check knowledge base structure and content."""
        logger.info("[HEALTH] Checking knowledge base...")
        
        try:
            kb_path = Path("knowledge_base")
            kb_exists = kb_path.exists()
            
            if not kb_exists:
                # Try to create it
                try:
                    kb_path.mkdir(parents=True, exist_ok=True)
                    kb_exists = True
                except:
                    pass
            
            if not kb_exists:
                return {
                    "status": "degraded",
                    "exists": False,
                    "note": "Knowledge base directory does not exist and could not be created"
                }
            
            # Create missing subdirectories
            layer1_path = kb_path / "layer_1"
            exports_path = kb_path / "exports"
            learning_memory_path = layer1_path / "learning_memory"
            
            try:
                layer1_path.mkdir(parents=True, exist_ok=True)
                exports_path.mkdir(parents=True, exist_ok=True)
                learning_memory_path.mkdir(parents=True, exist_ok=True)
            except:
                pass
            
            # Check subdirectories
            subdirs = {
                "layer_1": layer1_path.exists(),
                "exports": exports_path.exists(),
                "learning_memory": learning_memory_path.exists()
            }
            
            # Count files in knowledge base
            try:
                files = list(kb_path.rglob("*.*"))
                file_count = len([f for f in files if f.is_file()])
            except Exception:
                file_count = 0
            
            all_dirs_exist = all(subdirs.values())
            
            return {
                "status": "healthy" if kb_exists else "degraded",
                "exists": True,
                "file_count": file_count,
                "subdirectories": subdirs,
                "all_directories_present": all_dirs_exist,
                "note": "Created missing directories" if all_dirs_exist and kb_exists else None
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def run_all_checks(self):
        """Run all health checks."""
        logger.info("=" * 80)
        logger.info("GRACE SYSTEM HEALTH CHECK")
        logger.info("=" * 80)
        logger.info("")
        
        checks = [
            ("Database", self.check_database),
            ("File System", self.check_file_system),
            ("Memory Resources", self.check_memory_resources),
            ("Core Modules", self.check_core_modules),
            ("Genesis Key System", self.check_genesis_system),
            ("Self-Healing System", self.check_self_healing_system),
            ("Diagnostic System", self.check_diagnostic_system),
            ("Layer 1 System", self.check_layer1_system),
            ("File Ingestion System", self.check_ingestion_system),
            ("Knowledge Base", self.check_knowledge_base),
            ("Vector Database (Qdrant)", self.check_vector_database),  # Optional
            ("LLM Services (Ollama)", self.check_llm_services),  # Optional
            ("API Endpoints", self.check_api_endpoints),  # Optional
        ]
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                result["check_name"] = check_name
                self.results["checks"].append(result)
                
                status = result.get("status", "unknown")
                status_icon = "[OK]" if status == "healthy" else "[WARN]" if status == "degraded" else "[FAIL]"
                
                logger.info(f"{status_icon} {check_name}: {status}")
                
                if status == "healthy":
                    self.results["services_healthy"] += 1
                self.results["services_total"] += 1
                
            except Exception as e:
                logger.error(f"❌ {check_name}: Error during check - {e}")
                self.results["checks"].append({
                    "check_name": check_name,
                    "status": "error",
                    "error": str(e)
                })
                self.results["services_total"] += 1
        
        # Determine overall status
        # Separate required vs optional services
        required_checks = [c for c in self.results["checks"] if c["check_name"] not in 
                          ["Vector Database (Qdrant)", "LLM Services (Ollama)", "API Endpoints"]]
        optional_checks = [c for c in self.results["checks"] if c["check_name"] in 
                          ["Vector Database (Qdrant)", "LLM Services (Ollama)", "API Endpoints"]]
        
        required_healthy = sum(1 for c in required_checks if c.get("status") == "healthy")
        required_total = len(required_checks)
        required_percent = (required_healthy / required_total * 100) if required_total > 0 else 0
        
        optional_healthy = sum(1 for c in optional_checks if c.get("status") == "healthy")
        optional_total = len(optional_checks)
        
        healthy_count = self.results["services_healthy"]
        total_count = self.results["services_total"]
        health_percent = (healthy_count / total_count * 100) if total_count > 0 else 0
        
        # Use required services for overall status
        if required_percent >= 90:
            self.results["overall_status"] = "healthy"
        elif required_percent >= 75:
            self.results["overall_status"] = "degraded"
        else:
            self.results["overall_status"] = "unhealthy"
        
        self.results["required_services"] = {
            "healthy": required_healthy,
            "total": required_total,
            "percent": round(required_percent, 1)
        }
        self.results["optional_services"] = {
            "healthy": optional_healthy,
            "total": optional_total
        }
        
        self.results["end_time"] = datetime.now(UTC).isoformat()
        self.results["health_percent"] = round(health_percent, 1)
        
        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("HEALTH CHECK SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Overall Status: {self.results['overall_status'].upper()}")
        logger.info(f"Required Services: {required_healthy}/{required_total} ({required_percent:.1f}%)")
        logger.info(f"Optional Services: {optional_healthy}/{optional_total}")
        logger.info(f"Total Services: {healthy_count}/{total_count} ({health_percent:.1f}%)")
        logger.info("=" * 80)
        
        return self.results
    
    def save_results(self, output_file: Optional[Path] = None):
        """Save health check results to JSON file."""
        if output_file is None:
            output_file = Path(f"health_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\n[HEALTH] Results saved to: {output_file}")
        return output_file


def main():
    """Run system health check."""
    checker = SystemHealthChecker()
    results = checker.run_all_checks()
    checker.save_results()
    
    # Exit with appropriate code
    if results["overall_status"] == "healthy":
        return 0
    elif results["overall_status"] == "degraded":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
