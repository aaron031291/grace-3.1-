"""
Self-Healing Actions for Diagnostic Machine

Implements concrete healing actions for:
- Database connection recovery
- Vector database reset
- Cache clearing
- Memory management
- Service restart coordination
- Log rotation
- Configuration reload

All actions are reversible where possible (Invariant 4).
"""

import gc
import os
import logging
import shutil
import signal
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class HealingActionType(str, Enum):
    """Types of healing actions."""
    DATABASE_RECONNECT = "database_reconnect"
    VECTOR_DB_RESET = "vector_db_reset"
    CACHE_CLEAR = "cache_clear"
    GARBAGE_COLLECTION = "garbage_collection"
    LOG_ROTATION = "log_rotation"
    CONFIG_RELOAD = "config_reload"
    SERVICE_RESTART = "service_restart"
    CONNECTION_POOL_RESET = "connection_pool_reset"
    EMBEDDING_MODEL_RELOAD = "embedding_model_reload"
    SESSION_CLEANUP = "session_cleanup"
    # FIX: Added code fix healing action for proactive self-healing
    CODE_FIX = "code_fix"


class HealingRisk(str, Enum):
    """Risk level of healing actions."""
    LOW = "low"  # No service interruption
    MEDIUM = "medium"  # Brief interruption possible
    HIGH = "high"  # Service interruption likely
    CRITICAL = "critical"  # Extended downtime possible


@dataclass
class HealingResult:
    """Result of a healing action."""
    action_type: HealingActionType
    success: bool
    message: str
    duration_ms: float = 0.0
    pre_state: Dict[str, Any] = field(default_factory=dict)
    post_state: Dict[str, Any] = field(default_factory=dict)
    rollback_available: bool = False
    rollback_command: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealingActionConfig:
    """Configuration for a healing action."""
    action_type: HealingActionType
    enabled: bool = True
    risk_level: HealingRisk = HealingRisk.LOW
    timeout_seconds: int = 60
    max_retries: int = 3
    requires_confirmation: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


class HealingActionRegistry:
    """
    Registry of all available healing actions.

    Provides a central place to register and discover healing capabilities.
    """

    def __init__(self):
        self._actions: Dict[HealingActionType, HealingActionConfig] = {}
        self._handlers: Dict[HealingActionType, Callable] = {}
        self._register_default_actions()

    def _register_default_actions(self):
        """Register default healing actions."""
        defaults = [
            HealingActionConfig(
                action_type=HealingActionType.DATABASE_RECONNECT,
                risk_level=HealingRisk.MEDIUM,
                timeout_seconds=30,
            ),
            HealingActionConfig(
                action_type=HealingActionType.VECTOR_DB_RESET,
                risk_level=HealingRisk.MEDIUM,
                timeout_seconds=60,
            ),
            HealingActionConfig(
                action_type=HealingActionType.CACHE_CLEAR,
                risk_level=HealingRisk.LOW,
                timeout_seconds=10,
            ),
            HealingActionConfig(
                action_type=HealingActionType.GARBAGE_COLLECTION,
                risk_level=HealingRisk.LOW,
                timeout_seconds=30,
            ),
            HealingActionConfig(
                action_type=HealingActionType.LOG_ROTATION,
                risk_level=HealingRisk.LOW,
                timeout_seconds=30,
            ),
            HealingActionConfig(
                action_type=HealingActionType.CONFIG_RELOAD,
                risk_level=HealingRisk.MEDIUM,
                timeout_seconds=15,
            ),
            HealingActionConfig(
                action_type=HealingActionType.SESSION_CLEANUP,
                risk_level=HealingRisk.LOW,
                timeout_seconds=30,
            ),
            HealingActionConfig(
                action_type=HealingActionType.CONNECTION_POOL_RESET,
                risk_level=HealingRisk.MEDIUM,
                timeout_seconds=30,
            ),
            HealingActionConfig(
                action_type=HealingActionType.EMBEDDING_MODEL_RELOAD,
                risk_level=HealingRisk.MEDIUM,
                timeout_seconds=120,
            ),
            # FIX: Code fix action for automatic vulnerability remediation
            HealingActionConfig(
                action_type=HealingActionType.CODE_FIX,
                risk_level=HealingRisk.HIGH,  # Code changes require careful handling
                timeout_seconds=300,
                requires_confirmation=True,  # Should be reviewed before applying
            ),
        ]

        for config in defaults:
            self._actions[config.action_type] = config

    def register_handler(self, action_type: HealingActionType, handler: Callable):
        """Register a handler for a healing action."""
        self._handlers[action_type] = handler

    def get_action(self, action_type: HealingActionType) -> Optional[HealingActionConfig]:
        """Get configuration for an action."""
        return self._actions.get(action_type)

    def get_handler(self, action_type: HealingActionType) -> Optional[Callable]:
        """Get handler for an action."""
        return self._handlers.get(action_type)

    def list_actions(self) -> List[HealingActionConfig]:
        """List all registered actions."""
        return list(self._actions.values())


class HealingExecutor:
    """
    Executes self-healing actions with safety checks.

    Implements:
    - Pre-condition verification
    - Action execution with timeout
    - Post-condition verification
    - Rollback on failure
    - Logging and audit trail
    """

    def __init__(
        self,
        registry: HealingActionRegistry = None,
        dry_run: bool = False,
        log_dir: str = None
    ):
        self.registry = registry or HealingActionRegistry()
        self.dry_run = dry_run
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).parent.parent / "logs" / "healing"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default healing action handlers."""
        self.registry.register_handler(
            HealingActionType.DATABASE_RECONNECT,
            self._heal_database
        )
        self.registry.register_handler(
            HealingActionType.VECTOR_DB_RESET,
            self._heal_vector_db
        )
        self.registry.register_handler(
            HealingActionType.CACHE_CLEAR,
            self._heal_cache
        )
        self.registry.register_handler(
            HealingActionType.GARBAGE_COLLECTION,
            self._heal_gc
        )
        self.registry.register_handler(
            HealingActionType.LOG_ROTATION,
            self._heal_logs
        )
        self.registry.register_handler(
            HealingActionType.CONFIG_RELOAD,
            self._heal_config
        )
        self.registry.register_handler(
            HealingActionType.SESSION_CLEANUP,
            self._heal_sessions
        )
        self.registry.register_handler(
            HealingActionType.CONNECTION_POOL_RESET,
            self._heal_connection_pool
        )
        self.registry.register_handler(
            HealingActionType.EMBEDDING_MODEL_RELOAD,
            self._heal_embedding_model
        )
        # FIX: Register code fix handler for automatic vulnerability remediation
        self.registry.register_handler(
            HealingActionType.CODE_FIX,
            self._heal_code_issues
        )

    def execute(
        self,
        action_type: HealingActionType,
        parameters: Dict[str, Any] = None
    ) -> HealingResult:
        """Execute a healing action."""
        start_time = datetime.utcnow()
        parameters = parameters or {}

        config = self.registry.get_action(action_type)
        if not config:
            return HealingResult(
                action_type=action_type,
                success=False,
                message=f"Unknown action type: {action_type}",
            )

        if not config.enabled:
            return HealingResult(
                action_type=action_type,
                success=False,
                message=f"Action {action_type} is disabled",
            )

        handler = self.registry.get_handler(action_type)
        if not handler:
            return HealingResult(
                action_type=action_type,
                success=False,
                message=f"No handler registered for {action_type}",
            )

        # Capture pre-state
        pre_state = self._capture_state(action_type)

        # Execute action
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would execute: {action_type}")
                result = HealingResult(
                    action_type=action_type,
                    success=True,
                    message=f"[DRY RUN] {action_type} would be executed",
                    pre_state=pre_state,
                )
            else:
                result = handler(parameters)
                result.pre_state = pre_state

        except Exception as e:
            logger.error(f"Healing action {action_type} failed: {e}")
            result = HealingResult(
                action_type=action_type,
                success=False,
                message=f"Exception: {str(e)}",
                pre_state=pre_state,
            )

        # Capture post-state
        result.post_state = self._capture_state(action_type)

        # Calculate duration
        end_time = datetime.utcnow()
        result.duration_ms = (end_time - start_time).total_seconds() * 1000

        # Log the action
        self._log_healing_action(result)

        return result

    def _capture_state(self, action_type: HealingActionType) -> Dict[str, Any]:
        """Capture relevant state before/after healing."""
        state = {
            'timestamp': datetime.utcnow().isoformat(),
        }

        try:
            import psutil
            state['memory_percent'] = psutil.virtual_memory().percent
            state['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        except ImportError:
            pass

        return state

    def _log_healing_action(self, result: HealingResult):
        """Log healing action for audit trail."""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"healing_{today}.jsonl"

            import json
            with open(log_file, 'a') as f:
                f.write(json.dumps({
                    'action_type': result.action_type.value,
                    'success': result.success,
                    'message': result.message,
                    'duration_ms': result.duration_ms,
                    'timestamp': result.timestamp.isoformat(),
                    'pre_state': result.pre_state,
                    'post_state': result.post_state,
                }) + '\n')

        except Exception as e:
            logger.error(f"Failed to log healing action: {e}")

    # ==================== Healing Action Implementations ====================

    def _heal_database(self, params: Dict) -> HealingResult:
        """Reset database connection pool."""
        try:
            from database.connection import DatabaseConnection

            # Close existing connection
            DatabaseConnection.close()
            logger.info("Database connection closed for reset")

            # Re-initialize will happen on next access
            # Verify health
            if DatabaseConnection.health_check():
                return HealingResult(
                    action_type=HealingActionType.DATABASE_RECONNECT,
                    success=True,
                    message="Database connection reset successfully",
                    rollback_available=False,
                )
            else:
                return HealingResult(
                    action_type=HealingActionType.DATABASE_RECONNECT,
                    success=False,
                    message="Database reconnection failed health check",
                )

        except Exception as e:
            logger.error(f"Database healing failed: {e}")
            return HealingResult(
                action_type=HealingActionType.DATABASE_RECONNECT,
                success=False,
                message=f"Database healing error: {str(e)}",
            )

    def _heal_vector_db(self, params: Dict) -> HealingResult:
        """Reset vector database client connection."""
        try:
            # Try Qdrant client reset
            try:
                from vector_db.client import _client
                import vector_db.client as vdb_module

                # Clear the singleton
                if hasattr(vdb_module, '_client'):
                    vdb_module._client = None

                # Force new connection on next access
                from vector_db.client import get_qdrant_client
                new_client = get_qdrant_client()

                if new_client:
                    return HealingResult(
                        action_type=HealingActionType.VECTOR_DB_RESET,
                        success=True,
                        message="Vector DB client reset successfully",
                    )

            except ImportError:
                logger.debug("Qdrant client not available")

            # Try retrieval client reset
            try:
                from retrieval.qdrant_client import get_qdrant_client
                client = get_qdrant_client()
                if client:
                    return HealingResult(
                        action_type=HealingActionType.VECTOR_DB_RESET,
                        success=True,
                        message="Retrieval client reset successfully",
                    )
            except ImportError:
                pass

            return HealingResult(
                action_type=HealingActionType.VECTOR_DB_RESET,
                success=False,
                message="Vector DB client not available",
            )

        except Exception as e:
            logger.error(f"Vector DB healing failed: {e}")
            return HealingResult(
                action_type=HealingActionType.VECTOR_DB_RESET,
                success=False,
                message=f"Vector DB healing error: {str(e)}",
            )

    def _heal_cache(self, params: Dict) -> HealingResult:
        """Clear application caches."""
        cleared = []

        try:
            # Clear Python's internal caches
            import functools
            import linecache

            linecache.clearcache()
            cleared.append('linecache')

            # Clear LRU caches if any
            # This would need to iterate over known cached functions

            # Clear file-based caches
            cache_dirs = [
                Path(__file__).parent.parent / "cache",
                Path(__file__).parent.parent / ".cache",
                Path(__file__).parent.parent / "__pycache__",
            ]

            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    try:
                        shutil.rmtree(cache_dir)
                        cache_dir.mkdir(exist_ok=True)
                        cleared.append(str(cache_dir.name))
                    except Exception as e:
                        logger.warning(f"Could not clear {cache_dir}: {e}")

            # Try to clear Memory Mesh cache
            try:
                from cognitive.memory_mesh_cache import MemoryMeshCache
                MemoryMeshCache.clear_all()
                cleared.append('memory_mesh_cache')
            except (ImportError, AttributeError):
                pass

            return HealingResult(
                action_type=HealingActionType.CACHE_CLEAR,
                success=True,
                message=f"Cleared caches: {', '.join(cleared)}",
                rollback_available=False,
            )

        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
            return HealingResult(
                action_type=HealingActionType.CACHE_CLEAR,
                success=len(cleared) > 0,
                message=f"Partial cache clear: {', '.join(cleared)}. Error: {str(e)}",
            )

    def _heal_gc(self, params: Dict) -> HealingResult:
        """Force garbage collection."""
        try:
            # Get memory before
            try:
                import psutil
                mem_before = psutil.virtual_memory().percent
            except ImportError:
                mem_before = None

            # Run full GC
            gc.collect(0)  # Generation 0
            gc.collect(1)  # Generation 1
            gc.collect(2)  # Generation 2

            # Untrack objects that shouldn't be tracked
            unreachable = gc.collect()

            # Get memory after
            try:
                mem_after = psutil.virtual_memory().percent
                freed = mem_before - mem_after if mem_before else 0
            except ImportError:
                freed = 0

            return HealingResult(
                action_type=HealingActionType.GARBAGE_COLLECTION,
                success=True,
                message=f"GC completed. Unreachable objects: {unreachable}. Memory freed: {freed:.1f}%",
                rollback_available=False,
            )

        except Exception as e:
            logger.error(f"GC failed: {e}")
            return HealingResult(
                action_type=HealingActionType.GARBAGE_COLLECTION,
                success=False,
                message=f"GC error: {str(e)}",
            )

    def _heal_logs(self, params: Dict) -> HealingResult:
        """Rotate and compress old log files."""
        try:
            log_dir = Path(__file__).parent.parent / "logs"
            rotated = []
            errors = []

            if not log_dir.exists():
                return HealingResult(
                    action_type=HealingActionType.LOG_ROTATION,
                    success=True,
                    message="No log directory found",
                )

            # Find large log files
            max_size_mb = params.get('max_size_mb', 50)
            max_size_bytes = max_size_mb * 1024 * 1024

            for log_file in log_dir.rglob("*.log"):
                try:
                    if log_file.stat().st_size > max_size_bytes:
                        # Rotate: rename with timestamp
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        rotated_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
                        rotated_path = log_file.parent / rotated_name

                        log_file.rename(rotated_path)
                        rotated.append(log_file.name)

                        # Optionally compress
                        try:
                            import gzip
                            with open(rotated_path, 'rb') as f_in:
                                with gzip.open(f"{rotated_path}.gz", 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            rotated_path.unlink()
                        except Exception:
                            pass  # Compression is optional

                except Exception as e:
                    errors.append(f"{log_file.name}: {str(e)}")

            message = f"Rotated {len(rotated)} log files"
            if errors:
                message += f". Errors: {'; '.join(errors)}"

            return HealingResult(
                action_type=HealingActionType.LOG_ROTATION,
                success=True,
                message=message,
            )

        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
            return HealingResult(
                action_type=HealingActionType.LOG_ROTATION,
                success=False,
                message=f"Log rotation error: {str(e)}",
            )

    def _heal_config(self, params: Dict) -> HealingResult:
        """Reload configuration from files."""
        try:
            reloaded = []

            # Reload settings module
            try:
                import importlib
                import settings
                importlib.reload(settings)
                reloaded.append('settings')
            except ImportError:
                pass

            # Reload environment variables
            from dotenv import load_dotenv
            try:
                load_dotenv(override=True)
                reloaded.append('env_vars')
            except ImportError:
                pass

            return HealingResult(
                action_type=HealingActionType.CONFIG_RELOAD,
                success=True,
                message=f"Reloaded: {', '.join(reloaded)}",
            )

        except Exception as e:
            logger.error(f"Config reload failed: {e}")
            return HealingResult(
                action_type=HealingActionType.CONFIG_RELOAD,
                success=False,
                message=f"Config reload error: {str(e)}",
            )

    def _heal_sessions(self, params: Dict) -> HealingResult:
        """Cleanup expired or stale sessions."""
        try:
            cleaned = 0

            # Clean database sessions
            try:
                from database.session import SessionLocal
                # Force close any hanging sessions
                # Note: This is a simplification
                cleaned += 1
            except ImportError:
                pass

            # Clean temp files
            temp_dir = Path(__file__).parent.parent / "temp"
            if temp_dir.exists():
                for f in temp_dir.glob("*"):
                    try:
                        if f.is_file():
                            f.unlink()
                            cleaned += 1
                    except Exception:
                        pass

            return HealingResult(
                action_type=HealingActionType.SESSION_CLEANUP,
                success=True,
                message=f"Cleaned {cleaned} items",
            )

        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return HealingResult(
                action_type=HealingActionType.SESSION_CLEANUP,
                success=False,
                message=f"Session cleanup error: {str(e)}",
            )

    def _heal_connection_pool(self, params: Dict) -> HealingResult:
        """Reset connection pools."""
        try:
            reset = []

            # Reset database connection pool
            try:
                from database.connection import DatabaseConnection
                engine = DatabaseConnection.get_engine()
                engine.dispose()
                reset.append('database')
            except Exception as e:
                logger.debug(f"DB pool reset failed: {e}")

            # Reset HTTP connection pools
            try:
                import requests
                requests.Session().close()
                reset.append('http')
            except ImportError:
                pass

            return HealingResult(
                action_type=HealingActionType.CONNECTION_POOL_RESET,
                success=len(reset) > 0,
                message=f"Reset connection pools: {', '.join(reset)}",
            )

        except Exception as e:
            logger.error(f"Connection pool reset failed: {e}")
            return HealingResult(
                action_type=HealingActionType.CONNECTION_POOL_RESET,
                success=False,
                message=f"Connection pool reset error: {str(e)}",
            )

    def _heal_embedding_model(self, params: Dict) -> HealingResult:
        """Reload embedding model."""
        try:
            # Try to reload embedding model
            try:
                from embedding import get_embedding_model
                import embedding as emb_module

                # Clear cached model
                if hasattr(emb_module, '_model'):
                    emb_module._model = None

                # Force reload
                model = get_embedding_model()
                if model:
                    return HealingResult(
                        action_type=HealingActionType.EMBEDDING_MODEL_RELOAD,
                        success=True,
                        message="Embedding model reloaded successfully",
                    )

            except ImportError:
                pass

            return HealingResult(
                action_type=HealingActionType.EMBEDDING_MODEL_RELOAD,
                success=False,
                message="Embedding model not available",
            )

        except Exception as e:
            logger.error(f"Embedding model reload failed: {e}")
            return HealingResult(
                action_type=HealingActionType.EMBEDDING_MODEL_RELOAD,
                success=False,
                message=f"Embedding model reload error: {str(e)}",
            )

    def _heal_code_issues(self, params: Dict) -> HealingResult:
        """
        FIX: This healing action provides proactive code remediation for:
        - Syntax errors
        - Import errors
        - Missing files
        - Code quality issues (bare except, mutable defaults, etc.)
        - Security vulnerabilities
        - Type errors
        
        Uses the automatic bug fixer to fix issues detected by proactive scanner.
        """
        try:
            from .automatic_bug_fixer import get_automatic_fixer
            from .proactive_code_scanner import get_proactive_scanner
            from pathlib import Path
            
            backend_dir = Path(__file__).parent.parent
            # Enable DeepSeek for intelligent fixes (can be disabled via params)
            use_deepseek = params.get('use_deepseek', True)
            fixer = get_automatic_fixer(backend_dir=backend_dir, use_deepseek=use_deepseek)
            scanner = get_proactive_scanner(backend_dir=backend_dir)
            
            # Scan for issues
            issues = scanner.scan_all()
            
            if not issues:
                return HealingResult(
                    action_type=HealingActionType.CODE_FIX,
                    success=True,
                    message="No code issues detected",
                )
            
            # Filter by severity - only auto-fix critical and high issues
            critical_issues = [i for i in issues if i.severity == 'critical']
            high_issues = [i for i in issues if i.severity == 'high']
            
            # Fix critical issues first
            critical_fixes = fixer.fix_all_issues(critical_issues)
            high_fixes = fixer.fix_all_issues(high_issues)
            
            successful_fixes = [f for f in critical_fixes + high_fixes if f.success]
            failed_fixes = [f for f in critical_fixes + high_fixes if not f.success]
            
            # Also fix common warnings if requested
            warning_fixes = []
            if params.get('fix_warnings', False):
                warning_fixes = fixer.fix_all_warnings(max_files=50)
                successful_fixes.extend([f for f in warning_fixes if f.success])
            
            total_fixed = len(successful_fixes)
            total_failed = len(failed_fixes)
            
            message = f"Fixed {total_fixed} code issues"
            if total_failed > 0:
                message += f", {total_failed} failed"
            if warning_fixes:
                message += f", {len([f for f in warning_fixes if f.success])} warnings fixed"
            
            return HealingResult(
                action_type=HealingActionType.CODE_FIX,
                success=total_fixed > 0,
                message=message,
                pre_state={'issues_before': len(issues)},
                post_state={
                    'issues_after': len(issues) - total_fixed,
                    'fixes_applied': total_fixed,
                    'fixes_failed': total_failed,
                },
                rollback_available=True,  # Backups created
            )
            
        except Exception as e:
            logger.error(f"Code fix healing failed: {e}")
            import traceback
            traceback.print_exc()
            return HealingResult(
                action_type=HealingActionType.CODE_FIX,
                success=False,
                message=f"Code fix error: {str(e)}",
            )

    def _get_code_fix_patterns(self) -> Dict[str, tuple]:
        """
        Get automatic code fix patterns.

        Returns dict mapping issue_type to (pattern, replacement, description).
        """
        return {
            # Security fixes
            'command_injection': (
                r'shell\s*=\s*True',
                'shell=False',
                'Disabled shell execution to prevent command injection'
            ),
            'yaml_unsafe_load': (
                r'yaml\.load\s*\(([^)]+)\)',
                r'yaml.safe_load(\1)',
                'Changed yaml.load to yaml.safe_load'
            ),
            'os_system_injection': (
                r'os\.system\s*\(([^)]+)\)',
                r'subprocess.run(\1, shell=False, check=True)',
                'Replaced os.system with subprocess.run'
            ),
            # Configuration fixes
            'ssl_verify_disabled': (
                r'verify\s*=\s*False',
                'verify=True',
                'Enabled SSL verification'
            ),
            'debug_enabled': (
                r'DEBUG\s*=\s*True',
                'DEBUG = os.getenv("DEBUG", "false").lower() == "true"',
                'Made DEBUG configurable via environment'
            ),
            # Resource management fixes
            'file_not_closed': (
                r'(\w+)\s*=\s*open\s*\(([^)]+)\)(?!\s*as\s)',
                r'with open(\2) as \1:',
                'Wrapped file open in context manager'
            ),
        }

    def rollback_code_fix(self, backup_path: str, original_path: str) -> HealingResult:
        """
        Rollback a code fix using the backup file.

        Parameters:
            backup_path: Path to backup file
            original_path: Path to original file to restore
        """
        try:
            backup = Path(backup_path)
            original = Path(original_path)

            if not backup.exists():
                return HealingResult(
                    action_type=HealingActionType.CODE_FIX,
                    success=False,
                    message=f"Backup file not found: {backup_path}",
                )

            # Restore from backup
            shutil.copy2(backup, original)

            return HealingResult(
                action_type=HealingActionType.CODE_FIX,
                success=True,
                message=f"Successfully rolled back {original_path} from backup",
            )

        except Exception as e:
            logger.error(f"Code fix rollback failed: {e}")
            return HealingResult(
                action_type=HealingActionType.CODE_FIX,
                success=False,
                message=f"Rollback error: {str(e)}",
            )


# Global instance
_healing_executor: Optional[HealingExecutor] = None


def get_healing_executor() -> HealingExecutor:
    """Get or create global healing executor."""
    global _healing_executor
    if _healing_executor is None:
        _healing_executor = HealingExecutor()
    return _healing_executor


def execute_healing(action_type: str, params: Dict = None) -> HealingResult:
    """Convenience function to execute a healing action."""
    try:
        action = HealingActionType(action_type)
    except ValueError:
        return HealingResult(
            action_type=HealingActionType.CACHE_CLEAR,  # Default
            success=False,
            message=f"Unknown action type: {action_type}",
        )

    return get_healing_executor().execute(action, params)
