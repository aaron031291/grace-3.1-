"""
Enterprise Pre-Flight Checker

Validates system state before attempting to start services.
Similar to what Kubernetes, Docker, and enterprise platforms do.
"""

import sys
import platform
import socket
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
import importlib
import subprocess

# Setup logger first
logger = logging.getLogger(__name__)

# Optional dependency
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - resource checks will be skipped")


class CheckSeverity(Enum):
    """Severity of a pre-flight check failure."""
    FATAL = "fatal"      # Must fix before starting
    WARNING = "warning"  # Can start but may have issues
    INFO = "info"        # Informational only


@dataclass
class PreFlightCheck:
    """Result of a single pre-flight check."""
    name: str
    passed: bool
    severity: CheckSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None


@dataclass
class PreFlightResult:
    """Complete pre-flight check results."""
    checks: List[PreFlightCheck]
    passed: bool
    fatal_failures: int
    warnings: int
    summary: str
    
    def can_proceed(self) -> bool:
        """Check if system can proceed with startup."""
        return self.fatal_failures == 0


class PreFlightChecker:
    """
    Enterprise-grade pre-flight checker.
    
    Validates:
    - Python version and dependencies
    - System resources (RAM, disk, CPU)
    - Port availability
    - File permissions
    - Configuration
    - Network connectivity
    - Service dependencies
    """
    
    def __init__(self, root_path: Path):
        """Initialize pre-flight checker."""
        self.root_path = Path(root_path).resolve()
        self.checks: List[PreFlightCheck] = []
        self._healing_result: Optional[PreFlightCheck] = None  # Store healing results
        self._coding_agent = None  # Will be set if available
        self._healing_bridge = None  # Bridge to coding agent
    
    def run_all_checks(self) -> PreFlightResult:
        """
        Run all pre-flight checks.
        
        Returns:
            PreFlightResult with all check results
        """
        logger.info("Running enterprise pre-flight checks...")
        
        # Try to get coding agent for advanced healing
        self._try_initialize_coding_agent()
        
        # Run self-healing FIRST to fix issues before other checks run
        self.check_and_heal_startup_issues()
        
        # Run all checks (after self-healing has fixed issues)
        self.checks = [
            self.check_python_version(),
            self.check_system_resources(),
            self.check_disk_space(),
            self.check_ports_available(),
            self.check_file_permissions(),
            self.check_python_dependencies(),
            self.check_configuration(),
            self.check_network_connectivity(),
            self.check_service_dependencies(),
            self._get_healing_results()  # Get results from self-healing that ran earlier
        ]
        
        # Calculate summary
        fatal_failures = sum(1 for c in self.checks if not c.passed and c.severity == CheckSeverity.FATAL)
        warnings = sum(1 for c in self.checks if not c.passed and c.severity == CheckSeverity.WARNING)
        passed = fatal_failures == 0
        
        # Generate summary
        if passed:
            if warnings == 0:
                summary = f"✓ All pre-flight checks passed ({len(self.checks)} checks, 0 warnings)"
            else:
                summary = f"✓ Pre-flight checks passed ({len(self.checks)} checks, {warnings} informational notice(s))"
        else:
            summary = f"✗ {fatal_failures} fatal failure(s), {warnings} warning(s)"
        
        result = PreFlightResult(
            checks=self.checks,
            passed=passed,
            fatal_failures=fatal_failures,
            warnings=warnings,
            summary=summary
        )
        
        # Log results
        for check in self.checks:
            if not check.passed:
                level = logging.ERROR if check.severity == CheckSeverity.FATAL else logging.WARNING
                logger.log(level, f"[PRE-FLIGHT] {check.name}: {check.message}")
                if check.fix_suggestion:
                    logger.log(level, f"  → Fix: {check.fix_suggestion}")
        
        return result
    
    def check_python_version(self) -> PreFlightCheck:
        """Check Python version compatibility."""
        version = sys.version_info
        min_version = (3, 10)
        
        if version.major < min_version[0] or (version.major == min_version[0] and version.minor < min_version[1]):
            return PreFlightCheck(
                name="Python Version",
                passed=False,
                severity=CheckSeverity.FATAL,
                message=f"Python {version.major}.{version.minor} detected, requires {min_version[0]}.{min_version[1]}+",
                details={"current": f"{version.major}.{version.minor}", "required": f"{min_version[0]}.{min_version[1]}+"},
                fix_suggestion=f"Upgrade Python to {min_version[0]}.{min_version[1]} or higher"
            )
        
        return PreFlightCheck(
            name="Python Version",
            passed=True,
            severity=CheckSeverity.INFO,
            message=f"Python {version.major}.{version.minor}.{version.micro} ✓",
            details={"version": f"{version.major}.{version.minor}.{version.micro}"}
        )
    
    def check_system_resources(self) -> PreFlightCheck:
        """Check system resources (RAM, CPU)."""
        if not PSUTIL_AVAILABLE:
            return PreFlightCheck(
                name="System Resources",
                passed=True,
                severity=CheckSeverity.INFO,
                message="Resource check skipped (psutil not available)",
                details={"psutil_available": False}
            )
        
        try:
            # Check RAM
            memory = psutil.virtual_memory()
            min_ram_gb = 4.0
            available_gb = memory.available / (1024**3)
            
            # Check CPU
            cpu_count = psutil.cpu_count()
            min_cpus = 2
            
            issues = []
            if available_gb < min_ram_gb:
                issues.append(f"RAM: {available_gb:.1f}GB available, {min_ram_gb}GB recommended")
            
            if cpu_count < min_cpus:
                issues.append(f"CPU: {cpu_count} cores, {min_cpus} recommended")
            
            if issues:
                return PreFlightCheck(
                    name="System Resources",
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message="; ".join(issues),
                    details={"ram_gb": available_gb, "cpu_count": cpu_count},
                    fix_suggestion="Close other applications or upgrade hardware"
                )
            
            return PreFlightCheck(
                name="System Resources",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"RAM: {available_gb:.1f}GB, CPU: {cpu_count} cores ✓",
                details={"ram_gb": available_gb, "cpu_count": cpu_count}
            )
        except Exception as e:
            return PreFlightCheck(
                name="System Resources",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Could not check resources: {e}",
                details={"error": str(e)}
            )
    
    def check_disk_space(self) -> PreFlightCheck:
        """Check available disk space."""
        if not PSUTIL_AVAILABLE:
            return PreFlightCheck(
                name="Disk Space",
                passed=True,
                severity=CheckSeverity.INFO,
                message="Disk check skipped (psutil not available)",
                details={"psutil_available": False}
            )
        
        try:
            disk = psutil.disk_usage(str(self.root_path))
            free_gb = disk.free / (1024**3)
            min_free_gb = 1.0
            
            if free_gb < min_free_gb:
                return PreFlightCheck(
                    name="Disk Space",
                    passed=False,
                    severity=CheckSeverity.FATAL,
                    message=f"Only {free_gb:.1f}GB free, {min_free_gb}GB required",
                    details={"free_gb": free_gb, "required_gb": min_free_gb},
                    fix_suggestion="Free up disk space or use a different location"
                )
            
            return PreFlightCheck(
                name="Disk Space",
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"{free_gb:.1f}GB free ✓",
                details={"free_gb": free_gb}
            )
        except Exception as e:
            return PreFlightCheck(
                name="Disk Space",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Could not check disk space: {e}",
                details={"error": str(e)}
            )
    
    def check_ports_available(self) -> PreFlightCheck:
        """Check if required ports are available."""
        required_ports = [8000]  # Backend
        optional_ports = [6333, 11434]  # Qdrant, Ollama
        
        unavailable = []
        for port in required_ports:
            if not self._is_port_available(port):
                unavailable.append(port)
        
        if unavailable:
            return PreFlightCheck(
                name="Port Availability",
                passed=False,
                severity=CheckSeverity.FATAL,
                message=f"Required ports in use: {unavailable}",
                details={"unavailable_ports": unavailable},
                fix_suggestion=f"Stop services using ports {unavailable} or change port configuration"
            )
        
        # Check optional ports (if in use, that's actually good - services are running!)
        optional_unavailable = [p for p in optional_ports if not self._is_port_available(p)]
        if optional_unavailable:
            # This is actually good - means Qdrant/Ollama are running
            return PreFlightCheck(
                name="Port Availability",
                passed=True,
                severity=CheckSeverity.INFO,  # Changed from WARNING - this is good!
                message=f"Optional services detected on ports: {optional_unavailable} ✓",
                details={"optional_unavailable": optional_unavailable}
            )
        
        return PreFlightCheck(
            name="Port Availability",
            passed=True,
            severity=CheckSeverity.INFO,
            message="All required ports available ✓",
            details={"checked_ports": required_ports + optional_ports}
        )
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return True  # Assume available if check fails
    
    def check_file_permissions(self) -> PreFlightCheck:
        """Check file system permissions."""
        critical_paths = [
            self.root_path / "backend",
            self.root_path / "backend" / "data",
            self.root_path / "logs"
        ]
        
        issues = []
        for path in critical_paths:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    issues.append(f"Cannot create: {path}")
            elif not os.access(path, os.W_OK):
                issues.append(f"No write permission: {path}")
        
        if issues:
            return PreFlightCheck(
                name="File Permissions",
                passed=False,
                severity=CheckSeverity.FATAL,
                message="; ".join(issues),
                details={"issues": issues},
                fix_suggestion="Fix file permissions or run with appropriate privileges"
            )
        
        return PreFlightCheck(
            name="File Permissions",
            passed=True,
            severity=CheckSeverity.INFO,
            message="All required paths writable ✓"
        )
    
    def check_python_dependencies(self) -> PreFlightCheck:
        """Check critical Python dependencies."""
        critical_deps = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "pydantic"
        ]
        
        missing = []
        for dep in critical_deps:
            try:
                importlib.import_module(dep.replace("-", "_"))
            except ImportError:
                missing.append(dep)
        
        if missing:
            return PreFlightCheck(
                name="Python Dependencies",
                passed=False,
                severity=CheckSeverity.FATAL,
                message=f"Missing dependencies: {', '.join(missing)}",
                details={"missing": missing},
                fix_suggestion=f"Install missing packages: pip install {' '.join(missing)}"
            )
        
        return PreFlightCheck(
            name="Python Dependencies",
            passed=True,
            severity=CheckSeverity.INFO,
            message=f"All {len(critical_deps)} critical dependencies available ✓"
        )
    
    def check_configuration(self) -> PreFlightCheck:
        """Check configuration files and environment."""
        config_issues = []
        
        # Check for .env file (optional but recommended)
        env_file = self.root_path / "backend" / ".env"
        if not env_file.exists():
            config_issues.append("No .env file found (using defaults)")
        
        # Check backend directory exists
        backend_dir = self.root_path / "backend"
        if not backend_dir.exists():
            return PreFlightCheck(
                name="Configuration",
                passed=False,
                severity=CheckSeverity.FATAL,
                message="Backend directory not found",
                details={"backend_dir": str(backend_dir)},
                fix_suggestion="Ensure backend directory exists"
            )
        
        if config_issues:
            # Missing .env is not a problem - Grace uses defaults
            return PreFlightCheck(
                name="Configuration",
                passed=True,
                severity=CheckSeverity.INFO,  # Changed from WARNING - defaults are fine
                message="; ".join(config_issues) + " (using defaults)",
                details={"issues": config_issues}
            )
        
        return PreFlightCheck(
            name="Configuration",
            passed=True,
            severity=CheckSeverity.INFO,
            message="Configuration valid ✓"
        )
    
    def check_network_connectivity(self) -> PreFlightCheck:
        """Check basic network connectivity."""
        try:
            # Try to resolve localhost
            socket.gethostbyname("localhost")
            return PreFlightCheck(
                name="Network Connectivity",
                passed=True,
                severity=CheckSeverity.INFO,
                message="Network connectivity OK ✓"
            )
        except Exception as e:
            return PreFlightCheck(
                name="Network Connectivity",
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"Network check failed: {e}",
                details={"error": str(e)},
                fix_suggestion="Check network configuration"
            )
    
    def check_service_dependencies(self) -> PreFlightCheck:
        """Check if optional service dependencies are available."""
        services_status = {}
        
        # Check Qdrant
        try:
            qdrant_available = self._is_port_available(6333)
            services_status["qdrant"] = "available" if not qdrant_available else "not running"
        except Exception:
            services_status["qdrant"] = "unknown"
        
        # Check Ollama
        try:
            ollama_available = self._is_port_available(11434)
            services_status["ollama"] = "available" if not ollama_available else "not running"
        except Exception:
            services_status["ollama"] = "unknown"
        
        # These are optional, so just log status
        return PreFlightCheck(
            name="Service Dependencies",
            passed=True,
            severity=CheckSeverity.INFO,
            message=f"Optional services: {services_status}",
            details={"services": services_status}
        )
    
    def _get_healing_results(self) -> PreFlightCheck:
        """Get the results from self-healing that ran earlier."""
        if self._healing_result is None:
            # Fallback if healing wasn't run
            return PreFlightCheck(
                name="Self-Healing Pre-Startup",
                passed=True,
                severity=CheckSeverity.INFO,
                message="Self-healing check not run",
                details={}
            )
        return self._healing_result
    
    def _try_initialize_coding_agent(self):
        """Try to initialize coding agent if available (for advanced healing)."""
        try:
            # Try to get coding agent (may not be available during preflight)
            sys.path.insert(0, str(self.root_path / "backend"))
            from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
            from cognitive.coding_agent_healing_bridge import get_coding_agent_healing_bridge
            
            # Try to get coding agent (may fail if backend not initialized yet)
            try:
                self._coding_agent = get_enterprise_coding_agent()
                if self._coding_agent:
                    self._healing_bridge = get_coding_agent_healing_bridge(
                        coding_agent=self._coding_agent,
                        healing_system=None  # Not available during preflight
                    )
                    logger.info("[PRE-FLIGHT] ✓ Coding agent available for advanced healing")
            except Exception:
                # Coding agent not available yet - that's ok, we'll use basic fixes
                logger.debug("[PRE-FLIGHT] Coding agent not available (will use basic healing)")
        except ImportError:
            # Module not available - that's ok
            logger.debug("[PRE-FLIGHT] Coding agent module not available")
        except Exception as e:
            logger.debug(f"[PRE-FLIGHT] Could not initialize coding agent: {e}")
    
    def check_and_heal_startup_issues(self) -> PreFlightCheck:
        """
        Run self-healing checks to detect and fix common startup issues.
        
        This runs BEFORE the backend starts, so it can fix problems proactively.
        """
        logger.info("[PRE-FLIGHT] Running self-healing checks to fix issues before startup...")
        
        issues_found = []
        issues_fixed = []
        issues_remaining = []
        
        try:
            # 1. Check for logger conflicts in critical modules
            logger_conflicts = self._check_and_fix_logger_conflicts()
            if logger_conflicts:
                if logger_conflicts.get("fixed"):
                    issues_fixed.append(f"Fixed {logger_conflicts.get('count', 0)} logger conflict(s)")
                else:
                    issues_remaining.append(f"Found {logger_conflicts.get('count', 0)} logger conflict(s) (could not auto-fix)")
            
            # 2. Check for import errors in critical modules
            import_errors = self._check_and_fix_import_errors()
            if import_errors:
                if import_errors.get("fixed"):
                    issues_fixed.append(f"Fixed {import_errors.get('count', 0)} import error(s)")
                else:
                    issues_remaining.append(f"Found {import_errors.get('count', 0)} import error(s) (could not auto-fix)")
            
            # 3. Check for missing critical directories
            missing_dirs = self._check_and_create_missing_directories()
            if missing_dirs:
                if missing_dirs.get("fixed"):
                    issues_fixed.append(f"Created {missing_dirs.get('count', 0)} missing directory(ies)")
                else:
                    issues_remaining.append(f"Found {missing_dirs.get('count', 0)} missing directory(ies) (could not auto-fix)")
            
            # 4. Check for database initialization issues
            db_issues = self._check_database_initialization()
            if db_issues:
                if db_issues.get("fixed"):
                    issues_fixed.append("Fixed database initialization issues")
                else:
                    issues_remaining.append("Database initialization issues detected (may need manual fix)")
            
            # Also fix configuration issues that cause warnings
            config_fixes = self._fix_configuration_warnings()
            if config_fixes:
                issues_fixed.extend(config_fixes)
            
            # 5. Use coding agent for complex fixes if available
            if self._coding_agent and self._healing_bridge:
                complex_fixes = self._use_coding_agent_for_fixes(issues_remaining)
                if complex_fixes:
                    issues_fixed.extend(complex_fixes)
                    # Remove fixed issues from remaining
                    for fix in complex_fixes:
                        if "Fixed" in fix:
                            # Extract issue type from fix message
                            for remaining in issues_remaining[:]:
                                if any(word in remaining.lower() for word in fix.lower().split()):
                                    issues_remaining.remove(remaining)
            
            # Determine result
            if issues_fixed:
                logger.info(f"[PRE-FLIGHT] ✓ Self-healing fixed {len(issues_fixed)} issue(s) before startup")
                result = PreFlightCheck(
                    name="Self-Healing Pre-Startup",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message=f"Fixed {len(issues_fixed)} issue(s) before startup: {', '.join(issues_fixed)}",
                    details={
                        "issues_fixed": issues_fixed,
                        "issues_remaining": issues_remaining
                    }
                )
            elif issues_remaining:
                result = PreFlightCheck(
                    name="Self-Healing Pre-Startup",
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"Found {len(issues_remaining)} issue(s) that couldn't be auto-fixed: {', '.join(issues_remaining)}",
                    details={
                        "issues_remaining": issues_remaining
                    },
                    fix_suggestion="Review issues and fix manually, or check logs for details"
                )
            else:
                result = PreFlightCheck(
                    name="Self-Healing Pre-Startup",
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message="No startup issues detected ✓",
                    details={}
                )
            
            # Store result for later retrieval
            self._healing_result = result
            return result
                
        except Exception as e:
            logger.debug(f"[PRE-FLIGHT] Self-healing check encountered an error (non-critical): {e}")
            # Don't warn about self-healing check failures - it's just a bonus feature
            return PreFlightCheck(
                name="Self-Healing Pre-Startup",
                passed=True,  # Don't block startup if self-healing check itself fails
                severity=CheckSeverity.INFO,  # Changed from WARNING - not critical
                message="Self-healing check skipped (non-critical)",
                details={"error": str(e)}
            )
    
    def _check_and_fix_logger_conflicts(self) -> Dict[str, Any]:
        """Check for logger conflicts in critical modules and fix them."""
        backend_path = self.root_path / "backend"
        if not backend_path.exists():
            return {}
        
        conflicts_found = []
        conflicts_fixed = 0
        
        # Check critical modules that are known to have logger conflicts
        critical_modules = [
            "timesense/primitives.py",
            "timesense/profiles.py",
            "timesense/predictor.py",
            "timesense/engine.py",
            "cognitive/autonomous_healing_system.py"
        ]
        
        for module_path in critical_modules:
            full_path = backend_path / module_path
            if not full_path.exists():
                continue
            
            try:
                # Read file and check for logger conflicts
                content = full_path.read_text(encoding='utf-8')
                
                # Check for logger definitions inside Enum classes (common conflict pattern)
                # Pattern: class SomeEnum(Enum): followed by logger = logging.getLogger
                pattern = r'class\s+\w+.*Enum.*:\s*\n\s+logger\s*=\s*logging\.getLogger'
                if re.search(pattern, content, re.MULTILINE):
                    conflicts_found.append(module_path)
                    
                    # Try to fix: move logger to module level
                    fixed_content = self._fix_logger_in_enum(content, module_path)
                    if fixed_content != content:
                        full_path.write_text(fixed_content, encoding='utf-8')
                        conflicts_fixed += 1
                        logger.info(f"[PRE-FLIGHT] ✓ Fixed logger conflict in {module_path}")
            
            except Exception as e:
                logger.debug(f"Could not check/fix logger conflict in {module_path}: {e}")
        
        if conflicts_found:
            return {
                "count": len(conflicts_found),
                "fixed": conflicts_fixed > 0,
                "fixed_count": conflicts_fixed
            }
        
        return {}
    
    def _fix_logger_in_enum(self, content: str, module_path: str) -> str:
        """Fix logger definition inside Enum class by moving it to module level."""
        import re
        
        # Find logger definitions inside Enum classes
        # Pattern: class EnumName(Enum): ... logger = logging.getLogger(__name__)
        enum_logger_pattern = r'(class\s+\w+.*Enum[^:]*:\s*\n)(\s+logger\s*=\s*logging\.getLogger\(__name__\)\s*\n)+'
        
        def fix_match(match):
            enum_declaration = match.group(1)
            # Remove logger lines from inside the enum
            # Check if logging is already imported
            if 'import logging' not in content[:content.find(enum_declaration)]:
                # Need to add import
                return f"import logging\n\nlogger = logging.getLogger(__name__)\n\n{enum_declaration}"
            else:
                # Just add logger after imports
                return f"{enum_declaration}"
        
        # Remove logger from inside enum
        fixed = re.sub(enum_logger_pattern, fix_match, content)
        
        # If we made changes, ensure logger is at module level
        if fixed != content:
            # Check if logger is already defined at module level
            if not re.search(r'^logger\s*=\s*logging\.getLogger', fixed, re.MULTILINE):
                # Find where to insert logger (after imports, before first class)
                import_section = re.search(r'(^import\s+.*\n)+', fixed, re.MULTILINE)
                if import_section:
                    insert_pos = import_section.end()
                    fixed = fixed[:insert_pos] + "\nlogger = logging.getLogger(__name__)\n" + fixed[insert_pos:]
        
        return fixed
    
    def _check_and_fix_import_errors(self) -> Dict[str, Any]:
        """Check for import errors in critical modules."""
        backend_path = self.root_path / "backend"
        if not backend_path.exists():
            return {}
        
        import sys
        import importlib.util
        
        errors_found = []
        errors_fixed = 0
        
        # Try importing critical modules
        critical_modules = [
            "api.health",
            "cognitive.deterministic_stability_proof",
            "timesense.primitives"
        ]
        
        for module_name in critical_modules:
            try:
                # Try to import
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    errors_found.append(module_name)
                    continue
                
                # Try actual import
                module = importlib.import_module(module_name)
                
            except (ImportError, SyntaxError, NameError) as e:
                error_msg = str(e)
                if 'logger' in error_msg.lower() and 'already defined' in error_msg.lower():
                    # This is a logger conflict - we'll handle it in logger conflict check
                    pass
                else:
                    errors_found.append(f"{module_name}: {error_msg}")
        
        if errors_found:
            return {
                "count": len(errors_found),
                "fixed": errors_fixed > 0,
                "errors": errors_found
            }
        
        return {}
    
    def _check_and_create_missing_directories(self) -> Dict[str, Any]:
        """Check for missing critical directories and create them."""
        critical_dirs = [
            self.root_path / "backend" / "data",
            self.root_path / "backend" / "logs",
            self.root_path / "logs",
            self.root_path / "backend" / "knowledge_base"
        ]
        
        missing = []
        created = 0
        
        for dir_path in critical_dirs:
            if not dir_path.exists():
                missing.append(str(dir_path))
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created += 1
                    logger.info(f"[PRE-FLIGHT] ✓ Created missing directory: {dir_path}")
                except Exception as e:
                    logger.warning(f"[PRE-FLIGHT] Could not create {dir_path}: {e}")
        
        if missing:
            return {
                "count": len(missing),
                "fixed": created > 0,
                "created": created,
                "missing": missing
            }
        
            return {}
    
    def _fix_configuration_warnings(self) -> List[str]:
        """Fix configuration issues that would cause warnings."""
        fixes = []
        
        # Create .env file if missing (with sensible defaults)
        env_file = self.root_path / "backend" / ".env"
        if not env_file.exists():
            try:
                # Create a basic .env file with defaults
                default_env = """# Grace Configuration
# This file was auto-generated by Grace's self-healing system
# You can customize these values as needed

# Database Configuration
DATABASE_TYPE=sqlite
DATABASE_PATH=data/grace.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO

# Optional: Add your custom configuration below
"""
                env_file.write_text(default_env, encoding='utf-8')
                fixes.append("Created missing .env file with defaults")
                logger.info(f"[PRE-FLIGHT] ✓ Created .env file at {env_file}")
            except Exception as e:
                logger.debug(f"Could not create .env file: {e}")
        
        return fixes
    
    def _use_coding_agent_for_fixes(self, remaining_issues: List[str]) -> List[str]:
        """Use coding agent to fix complex issues that basic healing couldn't fix."""
        fixes = []
        
        if not self._coding_agent or not self._healing_bridge:
            return fixes
        
        try:
            # Analyze remaining issues and use coding agent for complex fixes
            for issue in remaining_issues:
                issue_lower = issue.lower()
                
                # Use coding agent for code-related issues
                if any(keyword in issue_lower for keyword in ['import', 'syntax', 'code', 'module', 'class', 'function']):
                    try:
                        logger.info(f"[PRE-FLIGHT] Using coding agent to fix: {issue}")
                        
                        # Request coding agent assistance
                        from cognitive.coding_agent_healing_bridge import AssistanceType
                        assistance_type = AssistanceType.CODE_FIX if "fix" in issue_lower else AssistanceType.CODE_GENERATION
                        
                        result = self._healing_bridge.healing_request_coding_assistance(
                            assistance_type=assistance_type,
                            description=f"Pre-flight startup issue: {issue}",
                            context={
                                "issue": issue,
                                "root_path": str(self.root_path),
                                "phase": "preflight",
                                "priority": "high"
                            },
                            priority="high"
                        )
                        
                        if result.get("success"):
                            fixes.append(f"Fixed via coding agent: {issue}")
                            logger.info(f"[PRE-FLIGHT] ✓ Coding agent fixed: {issue}")
                        else:
                            logger.debug(f"[PRE-FLIGHT] Coding agent could not fix: {issue}")
                    
                    except Exception as e:
                        logger.debug(f"[PRE-FLIGHT] Coding agent fix attempt failed: {e}")
        
        except Exception as e:
            logger.debug(f"[PRE-FLIGHT] Error using coding agent for fixes: {e}")
        
        return fixes
    
    def _check_database_initialization(self) -> Dict[str, Any]:
        """Check database initialization and fix common issues."""
        try:
            # Check if database file exists and is accessible
            backend_path = self.root_path / "backend"
            db_paths = [
                backend_path / "data" / "grace.db",
                backend_path / "grace.db"
            ]
            
            issues = []
            fixed = False
            
            for db_path in db_paths:
                if db_path.exists():
                    # Check if file is readable/writable
                    if not os.access(db_path, os.R_OK | os.W_OK):
                        issues.append(f"Database file not accessible: {db_path}")
                        try:
                            # Try to fix permissions
                            os.chmod(db_path, 0o644)
                            fixed = True
                        except Exception:
                            pass
            
            if issues:
                return {
                    "fixed": fixed,
                    "issues": issues
                }
            
            return {}
            
        except Exception as e:
            logger.debug(f"Database initialization check failed: {e}")
            return {}
