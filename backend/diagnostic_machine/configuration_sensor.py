import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ConfigurationIssue:
    """A configuration issue detected by the sensor."""
    issue_type: str  # 'missing_path', 'invalid_value', 'missing_env_var', 'service_unreachable'
    severity: str  # 'low', 'medium', 'high', 'critical'
    component: str  # 'embedding', 'database', 'qdrant', 'ollama', etc.
    message: str
    fix_suggestion: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfigurationSensorData:
    """Configuration validation sensor data."""
    issues: List[ConfigurationIssue] = field(default_factory=list)
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    components_checked: List[str] = field(default_factory=list)
    validation_passed: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConfigurationSensor:
    """
    Sensor that validates configuration before startup and during runtime.
    
    Detects:
    - Missing file paths (embedding models, config files)
    - Invalid environment variables
    - Missing required configuration
    - Service connectivity issues
    - Platform compatibility issues
    """
    
    def __init__(self, backend_dir: Optional[Path] = None):
        """Initialize configuration sensor."""
        if backend_dir is None:
            backend_dir = Path(__file__).parent.parent
        self.backend_dir = backend_dir
        
    def validate_all(self) -> ConfigurationSensorData:
        """Run all configuration validations."""
        data = ConfigurationSensorData()
        
        # Check embedding configuration
        data.issues.extend(self._validate_embedding_config())
        data.components_checked.append("embedding")
        
        # Check database configuration
        data.issues.extend(self._validate_database_config())
        data.components_checked.append("database")
        
        # Check Qdrant configuration
        data.issues.extend(self._validate_qdrant_config())
        data.components_checked.append("qdrant")
        
        # Check Ollama configuration
        data.issues.extend(self._validate_ollama_config())
        data.components_checked.append("ollama")
        
        # Check platform compatibility
        data.issues.extend(self._validate_platform_compatibility())
        data.components_checked.append("platform")
        
        # Check knowledge base paths
        data.issues.extend(self._validate_paths())
        data.components_checked.append("paths")
        
        # Check system resources (RAM, CPU, etc.)
        data.issues.extend(self._validate_system_resources())
        data.components_checked.append("system_resources")
        
        # Calculate totals
        data.total_issues = len(data.issues)
        data.critical_issues = sum(1 for i in data.issues if i.severity == 'critical')
        data.high_issues = sum(1 for i in data.issues if i.severity == 'high')
        data.medium_issues = sum(1 for i in data.issues if i.severity == 'medium')
        data.low_issues = sum(1 for i in data.issues if i.severity == 'low')
        data.validation_passed = data.critical_issues == 0 and data.high_issues == 0
        
        return data
    
    def _validate_embedding_config(self) -> List[ConfigurationIssue]:
        """Validate embedding model configuration."""
        issues = []
        
        try:
            from settings import settings
            
            # Check embedding model path
            model_path = Path(settings.EMBEDDING_MODEL_PATH)
            if not model_path.exists():
                issues.append(ConfigurationIssue(
                    issue_type='missing_path',
                    severity='medium',  # Not critical - model can be downloaded
                    component='embedding',
                    message=f"Embedding model path does not exist: {model_path}",
                    fix_suggestion=f"Download model or update EMBEDDING_MODEL_PATH. Model will need to be downloaded before embedding operations can be performed."
                ))
            
            # Check embedding device
            if settings.EMBEDDING_DEVICE not in ['cuda', 'cpu']:
                issues.append(ConfigurationIssue(
                    issue_type='invalid_value',
                    severity='high',
                    component='embedding',
                    message=f"Invalid EMBEDDING_DEVICE: {settings.EMBEDDING_DEVICE}. Must be 'cuda' or 'cpu'",
                    fix_suggestion="Set EMBEDDING_DEVICE to 'cuda' or 'cpu'"
                ))
            
            # Check if CUDA requested but not available
            if settings.EMBEDDING_DEVICE == 'cuda':
                try:
                    import torch
                    if not torch.cuda.is_available():
                        issues.append(ConfigurationIssue(
                            issue_type='invalid_value',
                            severity='medium',
                            component='embedding',
                            message="CUDA requested but not available",
                            fix_suggestion="Set EMBEDDING_DEVICE to 'cpu' or install CUDA-enabled PyTorch"
                        ))
                except ImportError:
                    pass
                    
        except Exception as e:
            issues.append(ConfigurationIssue(
                issue_type='validation_error',
                severity='high',
                component='embedding',
                message=f"Failed to validate embedding config: {e}",
                fix_suggestion="Check settings.py and environment variables"
            ))
        
        return issues
    
    def _validate_database_config(self) -> List[ConfigurationIssue]:
        """Validate database configuration."""
        issues = []
        
        try:
            from settings import settings
            
            # Check database type
            if settings.DATABASE_TYPE not in ['sqlite', 'postgresql', 'mysql']:
                issues.append(ConfigurationIssue(
                    issue_type='invalid_value',
                    severity='critical',
                    component='database',
                    message=f"Invalid DATABASE_TYPE: {settings.DATABASE_TYPE}",
                    fix_suggestion="Set DATABASE_TYPE to 'sqlite', 'postgresql', or 'mysql'"
                ))
            
            # Check SQLite path if using SQLite
            if settings.DATABASE_TYPE == 'sqlite':
                db_path = Path(settings.DATABASE_PATH)
                db_dir = db_path.parent
                if not db_dir.exists():
                    try:
                        db_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        issues.append(ConfigurationIssue(
                            issue_type='missing_path',
                            severity='critical',
                            component='database',
                            message=f"Database directory does not exist and cannot be created: {db_dir}",
                            fix_suggestion=f"Create directory: {db_dir} or update DATABASE_PATH"
                        ))
            
            # Check PostgreSQL/MySQL connection if configured
            if settings.DATABASE_TYPE in ['postgresql', 'mysql']:
                if not settings.DATABASE_HOST:
                    issues.append(ConfigurationIssue(
                        issue_type='missing_env_var',
                        severity='critical',
                        component='database',
                        message="DATABASE_HOST not set for PostgreSQL/MySQL",
                        fix_suggestion="Set DATABASE_HOST environment variable"
                    ))
                    
        except Exception as e:
            issues.append(ConfigurationIssue(
                issue_type='validation_error',
                severity='high',
                component='database',
                message=f"Failed to validate database config: {e}",
                fix_suggestion="Check settings.py and environment variables"
            ))
        
        return issues
    
    def _validate_qdrant_config(self) -> List[ConfigurationIssue]:
        """Validate Qdrant configuration."""
        issues = []
        
        try:
            from settings import settings
            
            # Check Qdrant host/port
            if not settings.QDRANT_HOST:
                issues.append(ConfigurationIssue(
                    issue_type='missing_env_var',
                    severity='high',
                    component='qdrant',
                    message="QDRANT_HOST not set",
                    fix_suggestion="Set QDRANT_HOST environment variable (default: localhost)"
                ))
            
            # Try to connect to Qdrant (non-blocking check)
            try:
                from vector_db.client import get_qdrant_client
                client = get_qdrant_client(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT
                )
                if not client.is_connected():
                    issues.append(ConfigurationIssue(
                        issue_type='service_unreachable',
                        severity='high',
                        component='qdrant',
                        message=f"Cannot connect to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
                        fix_suggestion=f"Ensure Qdrant is running at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
                    ))
            except Exception as e:
                issues.append(ConfigurationIssue(
                    issue_type='service_unreachable',
                    severity='medium',  # May not be running yet
                    component='qdrant',
                    message=f"Qdrant connection check failed: {e}",
                    fix_suggestion="Start Qdrant service or check connection settings"
                ))
                
        except Exception as e:
            issues.append(ConfigurationIssue(
                issue_type='validation_error',
                severity='medium',
                component='qdrant',
                message=f"Failed to validate Qdrant config: {e}",
                fix_suggestion="Check settings.py and Qdrant service status"
            ))
        
        return issues
    
    def _validate_ollama_config(self) -> List[ConfigurationIssue]:
        """Validate Ollama configuration."""
        issues = []
        
        try:
            from settings import settings
            
            # Check Ollama URL
            if not settings.OLLAMA_URL:
                issues.append(ConfigurationIssue(
                    issue_type='missing_env_var',
                    severity='high',
                    component='ollama',
                    message="OLLAMA_URL not set",
                    fix_suggestion="Set OLLAMA_URL environment variable (default: http://localhost:11434)"
                ))
            
            # Try to connect to Ollama (non-blocking check)
            try:
                import httpx
                response = httpx.get(f"{settings.OLLAMA_URL}/api/tags", timeout=2.0)
                if response.status_code != 200:
                    issues.append(ConfigurationIssue(
                        issue_type='service_unreachable',
                        severity='medium',
                        component='ollama',
                        message=f"Ollama service not responding at {settings.OLLAMA_URL}",
                        fix_suggestion="Start Ollama service or check OLLAMA_URL"
                    ))
            except Exception:
                # Ollama may not be running - this is OK for optional service
                issues.append(ConfigurationIssue(
                    issue_type='service_unreachable',
                    severity='low',  # Optional service
                    component='ollama',
                    message=f"Cannot reach Ollama at {settings.OLLAMA_URL}",
                    fix_suggestion="Ollama is optional - system can use external LLM service"
                ))
                
        except Exception as e:
            issues.append(ConfigurationIssue(
                issue_type='validation_error',
                severity='low',
                component='ollama',
                message=f"Failed to validate Ollama config: {e}",
                fix_suggestion="Check settings.py - Ollama is optional"
            ))
        
        return issues
    
    def _validate_platform_compatibility(self) -> List[ConfigurationIssue]:
        """Validate platform compatibility issues."""
        issues = []
        
        # Check for Windows multiprocessing issues
        if sys.platform == 'win32':
            # Check for files that use multiprocessing without proper guards
            test_files = list(self.backend_dir.parent.glob("tests/**/*.py"))
            for test_file in test_files[:10]:  # Check first 10 test files
                try:
                    content = test_file.read_text(encoding='utf-8')
                    # Check if uses multiprocessing but missing __main__ guard
                    if 'multiprocessing' in content or 'from multiprocessing' in content:
                        if 'if __name__' not in content and '__main__' not in content:
                            issues.append(ConfigurationIssue(
                                issue_type='platform_compatibility',
                                severity='high',
                                component='platform',
                                message=f"Test file {test_file.name} uses multiprocessing but may be missing __main__ guard for Windows compatibility",
                                fix_suggestion=f"Add 'if __name__ == \"__main__\": multiprocessing.freeze_support()' to {test_file.name}"
                            ))
                except Exception:
                    pass
        
        return issues
    
    def _validate_paths(self) -> List[ConfigurationIssue]:
        """Validate critical file paths."""
        issues = []
        
        # Check knowledge base path
        kb_path = self.backend_dir / "knowledge_base"
        if not kb_path.exists():
            try:
                kb_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(ConfigurationIssue(
                    issue_type='missing_path',
                    severity='medium',
                    component='paths',
                    message=f"Knowledge base directory does not exist and cannot be created: {kb_path}",
                    fix_suggestion=f"Create directory: {kb_path}"
                ))
        
        # Check data directory
        data_path = self.backend_dir / "data"
        if not data_path.exists():
            try:
                data_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(ConfigurationIssue(
                    issue_type='missing_path',
                    severity='medium',
                    component='paths',
                    message=f"Data directory does not exist and cannot be created: {data_path}",
                    fix_suggestion=f"Create directory: {data_path}"
                ))
        
        return issues
    
    def _validate_system_resources(self) -> List[ConfigurationIssue]:
        """Validate system resources (RAM, CPU, etc.)."""
        issues = []
        
        try:
            import psutil
            
            # Check RAM
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024 ** 3)
            memory_percent_used = memory.percent
            
            # On Windows, psutil.virtual_memory().available can be misleading due to
            # memory compression and caching. Use percentage-based check for better accuracy.
            # Windows can free cached/compressed memory when needed, so percentage is more reliable.
            
            # Configurable recommended RAM threshold
            # Set to 4GB as recommended for optimal Grace system performance
            # Can be adjusted via environment variable GRACE_MIN_RAM_GB if needed
            import os
            recommended_ram_gb = float(os.getenv('GRACE_MIN_RAM_GB', '4.0'))  # Default: 4GB minimum
            
            # Calculate available RAM for display (use free memory as it's more accurate on Windows)
            free_gb = memory.free / (1024 ** 3)
            # Also calculate based on percentage for comparison
            available_by_percent_gb = (total_gb * (100 - memory_percent_used) / 100)
            
            # Use the higher of the two values (more optimistic, accounts for Windows memory management)
            available_gb = max(free_gb, available_by_percent_gb)
            
            # Adaptive warning thresholds based on total RAM:
            # - Systems with >32GB RAM: Only warn if usage >98% AND available < 20GB (very lenient)
            # - Systems with 16-32GB RAM: Warn if usage >90% AND available < threshold  
            # - Systems with <16GB RAM: Warn if usage >85% AND available < threshold
            if total_gb > 32:
                # Large RAM systems: Very lenient - only warn if critically low
                # Set to 20GB minimum free for large systems to avoid false warnings
                warning_threshold_percent = 98  # Only warn at 98%+ usage
                min_free_gb = 20.0  # Require at least 20GB free on large systems
            elif total_gb > 16:
                # Medium RAM systems: Moderate threshold
                warning_threshold_percent = 90
                min_free_gb = recommended_ram_gb
            else:
                # Small RAM systems: More sensitive
                warning_threshold_percent = 85
                min_free_gb = recommended_ram_gb
            
            # Only warn if memory usage exceeds threshold AND available is below minimum
            # This avoids false positives on Windows where memory compression makes "available" look low
            # For large RAM systems, we're more lenient since even high % usage leaves plenty of RAM
            if memory_percent_used > warning_threshold_percent and available_gb < min_free_gb:
                # Use the appropriate threshold in the message (min_free_gb for large systems, recommended_ram_gb for others)
                threshold_display_gb = min_free_gb if total_gb > 32 else recommended_ram_gb
                issues.append(ConfigurationIssue(
                    issue_type='system_resource',
                    severity='low',  # Low severity - system can still function
                    component='system_resources',
                    message=f"RAM: {available_gb:.1f}GB available ({memory_percent_used:.1f}% used), {threshold_display_gb:.1f}GB recommended",
                    fix_suggestion=f"Consider closing other applications to free up RAM. System has {total_gb:.1f}GB total RAM."
                ))
                
        except ImportError:
            # psutil not available - skip check
            pass
        except Exception as e:
            logger.debug(f"Could not check system resources: {e}")
        
        return issues
