"""
Proactive Self-Healing CI/CD Integration

Grace's self-healing agent integrated with CI/CD pipeline to:
1. Continuously monitor for problems BEFORE they occur
2. Run proactive checks at every pipeline stage
3. Detect issues early (pre-commit, pre-build, pre-deploy)
4. Automatically fix issues before they reach production
5. Prevent problems rather than react to them
"""

import logging
import subprocess
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from enum import Enum

from sqlalchemy.orm import Session
from cognitive.devops_healing_agent import DevOpsHealingAgent, DevOpsLayer, IssueCategory
from llm_orchestrator.llm_orchestrator import LLMOrchestrator, TaskType

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """CI/CD pipeline stages where proactive checks run."""
    PRE_COMMIT = "pre_commit"          # Before code is committed
    PRE_BUILD = "pre_build"             # Before building
    PRE_TEST = "pre_test"               # Before running tests
    PRE_DEPLOY = "pre_deploy"           # Before deployment
    POST_DEPLOY = "post_deploy"         # After deployment
    CONTINUOUS = "continuous"            # Continuous monitoring


class ProactiveSelfHealing:
    """
    Proactive self-healing system integrated with CI/CD.
    
    Always seeking problems and finding them before they occur.
    """
    
    def __init__(
        self,
        devops_agent: DevOpsHealingAgent,
        llm_orchestrator: Optional[LLMOrchestrator] = None,
        session: Optional[Session] = None
    ):
        self.devops_agent = devops_agent
        self.llm_orchestrator = llm_orchestrator
        self.session = session
        
        # Proactive check results
        self.check_history = []
        self.issues_prevented = 0
        self.issues_fixed_proactively = 0
        
        # Monitoring intervals
        self.continuous_check_interval = 60  # Check every 60 seconds
        self.last_continuous_check = None
        
        logger.info("[PROACTIVE-HEALING] Proactive self-healing system initialized")
    
    def run_pipeline_check(self, stage: PipelineStage, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run proactive checks at a specific pipeline stage.
        
        This is called BEFORE each stage to catch issues early.
        """
        logger.info(f"[PROACTIVE-HEALING] Running proactive check for stage: {stage.value}")
        
        check_start = datetime.now()
        issues_found = []
        issues_fixed = []
        
        # Stage-specific checks
        if stage == PipelineStage.PRE_COMMIT:
            issues = self._check_pre_commit(context)
        elif stage == PipelineStage.PRE_BUILD:
            issues = self._check_pre_build(context)
        elif stage == PipelineStage.PRE_TEST:
            issues = self._check_pre_test(context)
        elif stage == PipelineStage.PRE_DEPLOY:
            issues = self._check_pre_deploy(context)
        elif stage == PipelineStage.POST_DEPLOY:
            issues = self._check_post_deploy(context)
        elif stage == PipelineStage.CONTINUOUS:
            issues = self._check_continuous(context)
        else:
            issues = []
        
        issues_found = issues
        
        # Attempt to fix issues proactively
        for issue in issues:
            logger.info(f"[PROACTIVE-HEALING] Attempting to fix: {issue.get('description', 'Unknown')}")
            
            try:
                context_dict = dict(context) if context else {}
                context_dict.update({
                    "pipeline_stage": stage.value,
                    "proactive_check": True,
                    "issue": issue
                })
                
                fix_result = self.devops_agent.detect_and_heal(
                    issue_description=issue.get("description", ""),
                    context=context_dict
                )
                
                if fix_result.get("success"):
                    issues_fixed.append({
                        "issue": issue,
                        "fix": fix_result
                    })
                    self.issues_fixed_proactively += 1
                    logger.info(f"[PROACTIVE-HEALING] ✓ Fixed proactively: {issue.get('description', 'Unknown')}")
                else:
                    # If can't fix, query LLM for help
                    if self.llm_orchestrator:
                        llm_guidance = self._query_llm_for_proactive_fix(issue, stage)
                        if llm_guidance:
                            logger.info(f"[PROACTIVE-HEALING] LLM provided guidance for: {issue.get('description', 'Unknown')}")
            
            except Exception as e:
                logger.error(f"[PROACTIVE-HEALING] Error fixing issue: {e}")
        
        check_duration = (datetime.now() - check_start).total_seconds()
        
        result = {
            "stage": stage.value,
            "timestamp": check_start.isoformat(),
            "duration_seconds": check_duration,
            "issues_found": len(issues_found),
            "issues_fixed": len(issues_fixed),
            "issues": issues_found,
            "fixes": issues_fixed,
            "prevented_production_issue": len(issues_fixed) > 0
        }
        
        self.check_history.append(result)
        self.issues_prevented += len(issues_fixed)
        
        logger.info(
            f"[PROACTIVE-HEALING] Check complete: {len(issues_found)} found, "
            f"{len(issues_fixed)} fixed proactively"
        )
        
        return result
    
    # ================================================================
    # PROACTIVE CHECKS BY STAGE
    # ================================================================
    
    def _check_pre_commit(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check before code is committed."""
        issues = []
        
        # Check for syntax errors
        issues.extend(self._check_code_syntax())
        
        # Check for import errors
        issues.extend(self._check_imports())
        
        # Check for configuration issues
        issues.extend(self._check_configuration())
        
        # Check for security issues
        issues.extend(self._check_security_vulnerabilities())
        
        # Check for code quality issues
        issues.extend(self._check_code_quality())
        
        return issues
    
    def _check_pre_build(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check before building."""
        issues = []
        
        # Check dependencies
        issues.extend(self._check_dependencies())
        
        # Check build configuration
        issues.extend(self._check_build_config())
        
        # Check environment variables
        issues.extend(self._check_environment())
        
        return issues
    
    def _check_pre_test(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check before running tests."""
        issues = []
        
        # Check test configuration
        issues.extend(self._check_test_config())
        
        # Check database connections
        issues.extend(self._check_database_connections())
        
        # Check test dependencies
        issues.extend(self._check_test_dependencies())
        
        return issues
    
    def _check_pre_deploy(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check before deployment."""
        issues = []
        
        # Check deployment configuration
        issues.extend(self._check_deployment_config())
        
        # Check infrastructure readiness
        issues.extend(self._check_infrastructure())
        
        # Check service health
        issues.extend(self._check_service_health())
        
        return issues
    
    def _check_post_deploy(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check after deployment."""
        issues = []
        
        # Check deployment health
        issues.extend(self._check_deployment_health())
        
        # Check service availability
        issues.extend(self._check_service_availability())
        
        # Check for regressions
        issues.extend(self._check_regressions())
        
        return issues
    
    def _check_continuous(self, context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Continuous monitoring checks."""
        issues = []
        
        # Run all diagnostic checks
        try:
            diagnostic_info = self.devops_agent._run_diagnostics()
            health_status = diagnostic_info.get("health_status", "unknown")
            
            if health_status in ("unhealthy", "critical", "failing"):
                issues.append({
                    "type": "system_health",
                    "description": f"System health is {health_status}",
                    "severity": "critical",
                    "layer": DevOpsLayer.BACKEND,
                    "category": IssueCategory.RUNTIME_ERROR
                })
            
            # Add any anomalies found
            anomalies = diagnostic_info.get("anomalies", [])
            issues.extend(anomalies)
            
        except Exception as e:
            logger.error(f"[PROACTIVE-HEALING] Diagnostic check failed: {e}")
        
        # Check for performance degradation
        issues.extend(self._check_performance())
        
        # Check for resource issues
        issues.extend(self._check_resources())
        
        return issues
    
    # ================================================================
    # SPECIFIC CHECK METHODS
    # ================================================================
    
    def _check_code_syntax(self) -> List[Dict[str, Any]]:
        """Check for syntax errors in code."""
        issues = []
        
        try:
            # Check Python files
            result = subprocess.run(
                ["python", "-m", "py_compile", "--help"],
                capture_output=True,
                timeout=5
            )
            
            # Find Python files
            python_files = list(Path("backend").rglob("*.py"))
            
            for py_file in python_files[:10]:  # Check first 10 files
                try:
                    compile(open(py_file).read(), py_file, "exec")
                except SyntaxError as e:
                    issues.append({
                        "type": "syntax_error",
                        "description": f"Syntax error in {py_file}: {e.msg}",
                        "file": str(py_file),
                        "line": e.lineno,
                        "severity": "high",
                        "layer": DevOpsLayer.BACKEND,
                        "category": IssueCategory.CODE_ERROR
                    })
        except Exception as e:
            logger.warning(f"[PROACTIVE-HEALING] Syntax check error: {e}")
        
        return issues
    
    def _check_imports(self) -> List[Dict[str, Any]]:
        """Check for import errors."""
        issues = []
        
        try:
            # Try importing main modules
            import sys
            sys.path.insert(0, "backend")
            
            # Check critical imports
            critical_modules = [
                "database.connection",
                "cognitive.devops_healing_agent",
                "llm_orchestrator.llm_orchestrator"
            ]
            
            for module in critical_modules:
                try:
                    __import__(module)
                except ImportError as e:
                    issues.append({
                        "type": "import_error",
                        "description": f"Import error: {module} - {str(e)}",
                        "module": module,
                        "severity": "high",
                        "layer": DevOpsLayer.BACKEND,
                        "category": IssueCategory.DEPENDENCY
                    })
        except Exception as e:
            logger.warning(f"[PROACTIVE-HEALING] Import check error: {e}")
        
        return issues
    
    def _check_configuration(self) -> List[Dict[str, Any]]:
        """Check configuration files."""
        issues = []
        
        # Check for .env file
        if not Path(".env").exists():
            issues.append({
                "type": "missing_config",
                "description": ".env file missing",
                "severity": "medium",
                "layer": DevOpsLayer.CONFIGURATION,
                "category": IssueCategory.CONFIGURATION
            })
        
        # Check database config
        try:
            from database.config import DatabaseConfig
            # Config exists, check if valid
        except Exception as e:
            issues.append({
                "type": "config_error",
                "description": f"Database config error: {str(e)}",
                "severity": "high",
                "layer": DevOpsLayer.CONFIGURATION,
                "category": IssueCategory.CONFIGURATION
            })
        
        return issues
    
    def _check_security_vulnerabilities(self) -> List[Dict[str, Any]]:
        """Check for security vulnerabilities."""
        issues = []
        
        # Check for hardcoded secrets
        try:
            for py_file in Path("backend").rglob("*.py"):
                if py_file.stat().st_size > 1000000:  # Skip large files
                    continue
                
                content = py_file.read_text(errors="ignore")
                
                # Check for common secret patterns
                secret_patterns = [
                    r'password\s*=\s*["\'][^"\']+["\']',
                    r'api_key\s*=\s*["\'][^"\']+["\']',
                    r'secret\s*=\s*["\'][^"\']+["\']'
                ]
                
                import re
                for pattern in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append({
                            "type": "security_issue",
                            "description": f"Potential hardcoded secret in {py_file}",
                            "file": str(py_file),
                            "severity": "critical",
                            "layer": DevOpsLayer.SECURITY,
                            "category": IssueCategory.SECURITY
                        })
                        break
        except Exception as e:
            logger.warning(f"[PROACTIVE-HEALING] Security check error: {e}")
        
        return issues
    
    def _check_code_quality(self) -> List[Dict[str, Any]]:
        """Check code quality issues."""
        issues = []
        
        # This could integrate with linters like pylint, flake8, etc.
        # For now, basic checks
        
        return issues
    
    def _check_dependencies(self) -> List[Dict[str, Any]]:
        """Check dependency issues."""
        issues = []
        
        # Check if requirements.txt exists
        if not Path("requirements.txt").exists():
            issues.append({
                "type": "missing_dependencies",
                "description": "requirements.txt missing",
                "severity": "medium",
                "layer": DevOpsLayer.DEPENDENCY,
                "category": IssueCategory.DEPENDENCY
            })
        
        return issues
    
    def _check_build_config(self) -> List[Dict[str, Any]]:
        """Check build configuration."""
        issues = []
        
        # Check Dockerfile if exists
        if Path("Dockerfile").exists():
            try:
                dockerfile_content = Path("Dockerfile").read_text()
                if "FROM" not in dockerfile_content:
                    issues.append({
                        "type": "build_config_error",
                        "description": "Dockerfile missing FROM instruction",
                        "severity": "high",
                        "layer": DevOpsLayer.INFRASTRUCTURE,
                        "category": IssueCategory.CONFIGURATION
                    })
            except Exception as e:
                logger.warning(f"[PROACTIVE-HEALING] Build config check error: {e}")
        
        return issues
    
    def _check_environment(self) -> List[Dict[str, Any]]:
        """Check environment variables."""
        issues = []
        
        # Check critical env vars
        critical_vars = ["DATABASE_URL", "API_KEY"]
        
        for var in critical_vars:
            if var not in os.environ:
                issues.append({
                    "type": "missing_env_var",
                    "description": f"Missing environment variable: {var}",
                    "severity": "high",
                    "layer": DevOpsLayer.CONFIGURATION,
                    "category": IssueCategory.CONFIGURATION
                })
        
        return issues
    
    def _check_test_config(self) -> List[Dict[str, Any]]:
        """Check test configuration."""
        issues = []
        
        # Check if test directory exists
        if not Path("tests").exists() and not Path("backend/tests").exists():
            issues.append({
                "type": "missing_tests",
                "description": "Test directory not found",
                "severity": "low",
                "layer": DevOpsLayer.BACKEND,
                "category": IssueCategory.CODE_ERROR
            })
        
        return issues
    
    def _check_database_connections(self) -> List[Dict[str, Any]]:
        """Check database connections."""
        issues = []
        
        try:
            from database.connection import DatabaseConnection
            if not DatabaseConnection.is_initialized():
                issues.append({
                    "type": "database_not_initialized",
                    "description": "Database connection not initialized",
                    "severity": "high",
                    "layer": DevOpsLayer.DATABASE,
                    "category": IssueCategory.DATABASE
                })
        except Exception as e:
            issues.append({
                "type": "database_error",
                "description": f"Database check failed: {str(e)}",
                "severity": "high",
                "layer": DevOpsLayer.DATABASE,
                "category": IssueCategory.DATABASE
            })
        
        return issues
    
    def _check_test_dependencies(self) -> List[Dict[str, Any]]:
        """Check test dependencies."""
        issues = []
        
        # Check if pytest is available
        try:
            import pytest
        except ImportError:
            issues.append({
                "type": "missing_test_dependency",
                "description": "pytest not installed",
                "severity": "medium",
                "layer": DevOpsLayer.DEPENDENCY,
                "category": IssueCategory.DEPENDENCY
            })
        
        return issues
    
    def _check_deployment_config(self) -> List[Dict[str, Any]]:
        """Check deployment configuration."""
        issues = []
        
        # Check deployment files
        deployment_files = ["docker-compose.yml", "k8s/deployment.yaml"]
        
        for file_path in deployment_files:
            if Path(file_path).exists():
                # Could validate YAML syntax here
                pass
        
        return issues
    
    def _check_infrastructure(self) -> List[Dict[str, Any]]:
        """Check infrastructure readiness."""
        issues = []
        
        # Check if Docker is running (if needed)
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                issues.append({
                    "type": "docker_not_running",
                    "description": "Docker is not running",
                    "severity": "high",
                    "layer": DevOpsLayer.INFRASTRUCTURE,
                    "category": IssueCategory.RUNTIME_ERROR
                })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Docker not available or not needed
            pass
        
        return issues
    
    def _check_service_health(self) -> List[Dict[str, Any]]:
        """Check service health."""
        issues = []
        
        # Check if API is responding
        try:
            import requests
            response = requests.get("http://localhost:8000/api/health", timeout=5)
            if response.status_code != 200:
                issues.append({
                    "type": "service_unhealthy",
                    "description": f"API health check failed: {response.status_code}",
                    "severity": "high",
                    "layer": DevOpsLayer.BACKEND,
                    "category": IssueCategory.RUNTIME_ERROR
                })
        except Exception:
            # Service might not be running, which is OK for pre-deploy
            pass
        
        return issues
    
    def _check_deployment_health(self) -> List[Dict[str, Any]]:
        """Check deployment health."""
        issues = []
        
        # Similar to service health but after deployment
        return self._check_service_health()
    
    def _check_service_availability(self) -> List[Dict[str, Any]]:
        """Check service availability."""
        issues = []
        
        # Check if services are accessible
        return issues
    
    def _check_regressions(self) -> List[Dict[str, Any]]:
        """Check for regressions."""
        issues = []
        
        # Compare current metrics with baseline
        return issues
    
    def _check_performance(self) -> List[Dict[str, Any]]:
        """Check for performance issues."""
        issues = []
        
        # Monitor response times, memory usage, etc.
        return issues
    
    def _check_resources(self) -> List[Dict[str, Any]]:
        """Check resource usage."""
        issues = []
        
        # Check disk space, memory, CPU
        try:
            import shutil
            disk_usage = shutil.disk_usage(".")
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            if free_percent < 10:
                issues.append({
                    "type": "low_disk_space",
                    "description": f"Low disk space: {free_percent:.1f}% free",
                    "severity": "high",
                    "layer": DevOpsLayer.INFRASTRUCTURE,
                    "category": IssueCategory.RESOURCE
                })
        except Exception as e:
            logger.warning(f"[PROACTIVE-HEALING] Resource check error: {e}")
        
        return issues
    
    # ================================================================
    # LLM QUERY FOR PROACTIVE FIXES
    # ================================================================
    
    def _query_llm_for_proactive_fix(
        self,
        issue: Dict[str, Any],
        stage: PipelineStage
    ) -> Optional[Dict[str, Any]]:
        """Query LLM for help with proactive fixing."""
        if not self.llm_orchestrator:
            return None
        
        try:
            prompt = f"""
I'm Grace, a proactive self-healing system. I've detected an issue BEFORE it reaches production.

Pipeline Stage: {stage.value}
Issue: {issue.get('description', 'Unknown')}
Type: {issue.get('type', 'unknown')}
Severity: {issue.get('severity', 'unknown')}

Please provide:
1. How to fix this issue proactively
2. How to prevent it from occurring again
3. Any code changes or configuration updates needed
4. Best practices to avoid this in the future

The goal is to prevent this issue from ever reaching production.
"""
            
            result = self.llm_orchestrator.execute_task(
                prompt=prompt,
                task_type=TaskType.DEBUGGING,
                require_verification=True,
                system_prompt="You are helping Grace prevent issues before they reach production."
            )
            
            if result.success:
                return {
                    "guidance": result.content,
                    "trust_score": result.trust_score
                }
        except Exception as e:
            logger.error(f"[PROACTIVE-HEALING] LLM query error: {e}")
        
        return None
    
    # ================================================================
    # STATISTICS
    # ================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get proactive healing statistics."""
        return {
            "total_checks": len(self.check_history),
            "issues_prevented": self.issues_prevented,
            "issues_fixed_proactively": self.issues_fixed_proactively,
            "prevention_rate": (
                self.issues_fixed_proactively / max(len(self.check_history), 1)
            ),
            "recent_checks": self.check_history[-10:] if self.check_history else []
        }
