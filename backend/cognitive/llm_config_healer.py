"""
LLM-Powered Configuration Healing System

Adaptive configuration error detection and fixing with LLM reasoning.
Handles:
- Missing configuration values
- Invalid configuration values
- Configuration file syntax errors (.env, YAML, JSON, Python)
- Environment variable issues
- Configuration mismatches after dependency upgrades
- Service-specific configuration errors

Features:
- LLM reasoning for context-aware fixes
- Dependency upgrade adaptation
- Configuration validation and auto-fix
- Integration with self-healing system
"""

import logging
import re
import os
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfigError:
    """Represents a detected configuration error."""
    error_type: str  # "missing_value", "invalid_value", "syntax_error", "mismatch", "deprecated"
    severity: str  # "critical", "high", "medium", "low"
    config_key: Optional[str] = None  # The configuration key (e.g., "OLLAMA_URL")
    config_file: Optional[str] = None  # Path to config file (e.g., ".env", "settings.py")
    current_value: Optional[str] = None  # Current (invalid) value
    error_message: Optional[str] = None  # Original error message
    description: str = ""
    reasoning: str = ""  # LLM's reasoning about the fix
    suggested_value: Optional[str] = None  # The correct configuration value
    suggested_fix: Optional[str] = None  # Full fix including reasoning
    confidence: float = 0.5  # 0.0-1.0
    dependency_info: Optional[Dict[str, Any]] = None  # Info about dependency versions
    service: Optional[str] = None  # Affected service (e.g., "database", "qdrant", "ollama")


class LLMConfigHealer:
    """
    Uses LLM reasoning to detect and fix configuration errors adaptively.
    
    Features:
    - Detects missing/invalid configuration values
    - Handles configuration file syntax errors
    - Adapts to dependency upgrade issues
    - Uses LLM to reason about correct values
    - Validates configuration against service requirements
    """
    
    def __init__(self, llm_service=None, repo_path: Optional[Path] = None):
        """
        Initialize LLM Config Healer.
        
        Args:
            llm_service: Optional LLM service instance
            repo_path: Optional repository path for config file searches
        """
        self.llm_service = llm_service
        if not self.llm_service:
            try:
                from llm_orchestrator.llm_service import get_llm_service
                self.llm_service = get_llm_service()
            except Exception as e:
                logger.warning(f"Could not initialize LLM service: {e}")
        
        self.repo_path = repo_path or Path.cwd()
        self._config_cache = {}  # Cache for config values
        self._dependency_cache = {}  # Cache for dependency info
    
    def detect_config_errors(
        self,
        error_message: Optional[str] = None,
        service: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ConfigError]:
        """
        Detect configuration errors using error messages and validation.
        
        Args:
            error_message: Optional error message from runtime
            service: Optional service name (e.g., "database", "qdrant")
            context: Optional context (dependency versions, recent changes, etc.)
            
        Returns:
            List of detected ConfigError objects
        """
        errors = []
        
        # 1. Parse error messages for config-related errors
        if error_message:
            parsed_errors = self._parse_error_message(error_message, service)
            errors.extend(parsed_errors)
        
        # 2. Validate current configuration
        validation_errors = self._validate_configuration(service)
        errors.extend(validation_errors)
        
        # 3. Use LLM to analyze and suggest fixes for each error
        if self.llm_service:
            for error in errors:
                llm_fix = self._llm_analyze_config_error(error, context)
                if llm_fix:
                    # Update error with LLM reasoning and fix
                    error.reasoning = llm_fix.get("reasoning", "")
                    error.suggested_value = llm_fix.get("suggested_value")
                    error.suggested_fix = llm_fix.get("suggested_fix")
                    error.confidence = llm_fix.get("confidence", error.confidence)
                    error.dependency_info = llm_fix.get("dependency_info")
        
        return errors
    
    def _parse_error_message(
        self,
        error_message: str,
        service: Optional[str] = None
    ) -> List[ConfigError]:
        """Parse error messages for configuration-related errors."""
        errors = []
        
        # Missing environment variable
        missing_env = re.search(
            r"(?:environment variable|env var|config) ['\"]?(\w+)['\"]? (?:is not set|not found|missing)",
            error_message,
            re.IGNORECASE
        )
        if missing_env:
            config_key = missing_env.group(1)
            errors.append(ConfigError(
                error_type="missing_value",
                severity="critical",
                config_key=config_key,
                error_message=error_message,
                description=f"Configuration '{config_key}' is missing",
                service=service,
                confidence=0.9
            ))
        
        # Invalid configuration value
        invalid_value = re.search(
            r"(?:invalid|bad|incorrect).*?config(?:uration)?.*?['\"]?(\w+)['\"]?",
            error_message,
            re.IGNORECASE
        )
        if invalid_value:
            config_key = invalid_value.group(1)
            errors.append(ConfigError(
                error_type="invalid_value",
                severity="high",
                config_key=config_key,
                error_message=error_message,
                description=f"Configuration '{config_key}' has invalid value",
                service=service,
                confidence=0.8
            ))
        
        # Connection errors that might be config-related
        connection_error = re.search(
            r"(?:connection|connect|connection error).*?(?:failed|refused|timeout)",
            error_message,
            re.IGNORECASE
        )
        if connection_error and service:
            # Could be config issue (wrong host/port)
            errors.append(ConfigError(
                error_type="mismatch",
                severity="critical",
                error_message=error_message,
                description=f"Connection error for {service} - possible configuration issue",
                service=service,
                confidence=0.6  # Lower confidence - might not be config
            ))
        
        # Settings validation errors
        validation_error = re.search(
            r"Settings validation failed.*?:\s*(.+)",
            error_message,
            re.IGNORECASE | re.DOTALL
        )
        if validation_error:
            details = validation_error.group(1)
            # Extract individual errors
            for line in details.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    config_key_match = re.search(r"['\"]?(\w+)['\"]?", line)
                    if config_key_match:
                        config_key = config_key_match.group(1)
                        errors.append(ConfigError(
                            error_type="invalid_value",
                            severity="high",
                            config_key=config_key,
                            error_message=error_message,
                            description=line[2:],  # Remove '- ' prefix
                            confidence=0.85
                        ))
        
        return errors
    
    def _validate_configuration(self, service: Optional[str] = None) -> List[ConfigError]:
        """Validate current configuration against requirements."""
        errors = []
        
        try:
            # Validate Settings
            from settings import Settings
            try:
                Settings.validate()
            except ValueError as e:
                # Parse validation errors
                error_msg = str(e)
                if "validation failed" in error_msg.lower():
                    for line in error_msg.split('\n'):
                        if line.strip().startswith('- '):
                            config_key_match = re.search(r"['\"]?(\w+)['\"]?", line)
                            if config_key_match:
                                config_key = config_key_match.group(1)
                                errors.append(ConfigError(
                                    error_type="invalid_value",
                                    severity="high",
                                    config_key=config_key,
                                    error_message=error_msg,
                                    description=line[2:],
                                    confidence=0.85
                                ))
        except Exception as e:
            logger.debug(f"[CONFIG-HEALER] Could not validate Settings: {e}")
        
        # Service-specific validation
        if service == "database":
            errors.extend(self._validate_database_config())
        elif service == "qdrant":
            errors.extend(self._validate_qdrant_config())
        elif service == "ollama":
            errors.extend(self._validate_ollama_config())
        
        return errors
    
    def _validate_database_config(self) -> List[ConfigError]:
        """Validate database configuration."""
        errors = []
        
        try:
            from database.config import DatabaseConfig
            from database.connection import DatabaseConnection
            
            # Check if database connection works
            if not DatabaseConnection.health_check():
                errors.append(ConfigError(
                    error_type="mismatch",
                    severity="critical",
                    service="database",
                    description="Database health check failed - possible configuration issue",
                    confidence=0.7
                ))
        except Exception as e:
            logger.debug(f"[CONFIG-HEALER] Database validation failed: {e}")
        
        return errors
    
    def _validate_qdrant_config(self) -> List[ConfigError]:
        """Validate Qdrant configuration."""
        errors = []
        
        try:
            from settings import Settings
            from vector_db.client import get_qdrant_client
            
            # Check if Qdrant host/port are set
            if not Settings.QDRANT_HOST:
                errors.append(ConfigError(
                    error_type="missing_value",
                    severity="high",
                    config_key="QDRANT_HOST",
                    service="qdrant",
                    description="QDRANT_HOST is not configured",
                    confidence=0.9
                ))
            
            # Try to connect
            try:
                client = get_qdrant_client()
                if not client:
                    errors.append(ConfigError(
                        error_type="mismatch",
                        severity="critical",
                        service="qdrant",
                        description="Qdrant client creation failed - check configuration",
                        confidence=0.8
                    ))
            except Exception:
                errors.append(ConfigError(
                    error_type="mismatch",
                    severity="critical",
                    service="qdrant",
                    description="Qdrant connection failed - check host/port configuration",
                    confidence=0.8
                ))
        except Exception as e:
            logger.debug(f"[CONFIG-HEALER] Qdrant validation failed: {e}")
        
        return errors
    
    def _validate_ollama_config(self) -> List[ConfigError]:
        """Validate Ollama configuration."""
        errors = []
        
        try:
            from settings import Settings
            from ollama_client.client import get_ollama_client
            
            # Check if Ollama URL is set
            if not Settings.OLLAMA_URL:
                errors.append(ConfigError(
                    error_type="missing_value",
                    severity="high",
                    config_key="OLLAMA_URL",
                    service="ollama",
                    description="OLLAMA_URL is not configured",
                    confidence=0.9
                ))
            
            # Try to connect
            try:
                client = get_ollama_client()
                if not client or not client.is_running():
                    errors.append(ConfigError(
                        error_type="mismatch",
                        severity="warning",
                        service="ollama",
                        description="Ollama service not running or not accessible",
                        confidence=0.7
                    ))
            except Exception:
                errors.append(ConfigError(
                    error_type="mismatch",
                    severity="warning",
                    service="ollama",
                    description="Ollama connection failed - check URL configuration",
                    confidence=0.7
                ))
        except Exception as e:
            logger.debug(f"[CONFIG-HEALER] Ollama validation failed: {e}")
        
        return errors
    
    def _llm_analyze_config_error(
        self,
        error: ConfigError,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to analyze configuration error and suggest fix.
        
        This is where the adaptive reasoning happens:
        - Handles dependency upgrades
        - Finds correct configuration values
        - Understands service requirements
        """
        if not self.llm_service:
            return None
        
        # Get dependency information
        dependency_info = self._get_dependency_info(context)
        
        # Get current configuration
        current_config = self._get_current_config(error.config_key, error.service)
        
        # Build prompt for LLM
        prompt = self._build_config_healing_prompt(error, current_config, dependency_info, context)
        
        try:
            response = self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2,  # Low temperature for deterministic fixes
                system_prompt=self._get_system_prompt()
            )
            
            # Parse LLM response
            fix = self._parse_llm_response(response, error)
            return fix
            
        except Exception as e:
            logger.error(f"[CONFIG-HEALER] LLM analysis failed: {e}")
            return None
    
    def _build_config_healing_prompt(
        self,
        error: ConfigError,
        current_config: Dict[str, Any],
        dependency_info: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for LLM configuration healing."""
        
        dependency_str = ""
        if dependency_info:
            dep_list = [f"{name}=={version}" for name, version in dependency_info.items()]
            dependency_str = f"\nInstalled Dependencies:\n" + "\n".join(dep_list)
        
        config_str = ""
        if current_config:
            config_str = "\nCurrent Configuration:\n" + json.dumps(current_config, indent=2)
        
        context_str = ""
        if context:
            if "recent_changes" in context:
                context_str += f"\nRecent Changes: {context['recent_changes']}\n"
            if "dependency_upgrade" in context:
                context_str += f"\nDependency Upgrade Detected: {context['dependency_upgrade']}\n"
        
        prompt = f"""Analyze this configuration error and suggest the correct fix:

Error Type: {error.error_type}
Service: {error.service or 'N/A'}
Config Key: {error.config_key or 'N/A'}
{dependency_str}
{config_str}
{context_str}

Error Details:
- Current Value: {error.current_value or 'N/A'}
- Error Message: {error.error_message or 'N/A'}
- Description: {error.description}

Consider:
1. **Missing Value**: Add the configuration with appropriate default or required value
2. **Invalid Value**: Fix the value format, type, or range
3. **Dependency Upgrade**: Configuration may have changed after dependency upgrade
4. **Service Requirements**: Check what the service actually needs
5. **Environment Variables**: Ensure .env file has correct format

For dependency upgrades, consider:
- Configuration format changes (e.g., connection string format)
- New required configuration keys
- Deprecated configuration keys
- Default value changes

Provide your analysis in this JSON format:
{{
  "reasoning": "Your step-by-step reasoning about why this config error occurred and how to fix it",
  "suggested_value": "the correct configuration value",
  "suggested_fix": "Full fix explanation including where to set it (.env file, settings.py, etc.)",
  "confidence": 0.0-1.0,
  "dependency_info": {{
    "package_name": "package that requires this config",
    "version_requirement": "version where this config format is valid",
    "alternative_if_deprecated": "alternative config if deprecated"
  }},
  "config_file": ".env or settings.py or other",
  "config_format": "KEY=value or KEY: value or other"
}}

Focus on being specific and accurate. For dependency upgrades, explain what changed and why.
"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for configuration healing."""
        return """You are an expert system administrator specializing in configuration management and 
dependency upgrades. You understand:
- Configuration file formats (.env, YAML, JSON, Python config files)
- Service-specific configuration requirements
- Common configuration errors and fixes
- How dependency upgrades affect configuration
- Environment variable best practices

You provide clear, accurate configuration fixes with reasoning, especially for dependency upgrade scenarios.
You adapt your suggestions based on installed dependency versions and service requirements."""
    
    def _parse_llm_response(
        self,
        response: str,
        error: ConfigError
    ) -> Optional[Dict[str, Any]]:
        """Parse LLM response into fix dictionary."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {
                    "reasoning": data.get("reasoning", ""),
                    "suggested_value": data.get("suggested_value"),
                    "suggested_fix": data.get("suggested_fix", ""),
                    "confidence": data.get("confidence", 0.7),
                    "dependency_info": data.get("dependency_info"),
                    "config_file": data.get("config_file", ".env"),
                    "config_format": data.get("config_format", "KEY=value")
                }
        except Exception as e:
            logger.warning(f"[CONFIG-HEALER] Failed to parse LLM JSON response: {e}")
        
        # Fallback: Extract config value from text
        value_match = re.search(
            r"(?:KEY|CONFIG|VALUE)[=:]\s*([^\s\n]+)",
            response,
            re.IGNORECASE
        )
        if value_match:
            return {
                "reasoning": response[:500],
                "suggested_value": value_match.group(1),
                "suggested_fix": response,
                "confidence": 0.6,
                "dependency_info": None,
                "config_file": ".env",
                "config_format": "KEY=value"
            }
        
        return None
    
    def _get_current_config(
        self,
        config_key: Optional[str] = None,
        service: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current configuration values."""
        config = {}
        
        try:
            from settings import Settings
            
            if config_key:
                # Get specific key
                if hasattr(Settings, config_key):
                    config[config_key] = getattr(Settings, config_key)
            elif service:
                # Get service-specific config
                if service == "database":
                    config.update({
                        "DATABASE_TYPE": Settings.DATABASE_TYPE,
                        "DATABASE_HOST": Settings.DATABASE_HOST,
                        "DATABASE_PORT": Settings.DATABASE_PORT,
                        "DATABASE_NAME": Settings.DATABASE_NAME,
                    })
                elif service == "qdrant":
                    config.update({
                        "QDRANT_HOST": Settings.QDRANT_HOST,
                        "QDRANT_PORT": Settings.QDRANT_PORT,
                    })
                elif service == "ollama":
                    config.update({
                        "OLLAMA_URL": Settings.OLLAMA_URL,
                        "OLLAMA_LLM_DEFAULT": Settings.OLLAMA_LLM_DEFAULT,
                    })
            else:
                # Get all config
                config = Settings.to_dict()
        except Exception as e:
            logger.debug(f"[CONFIG-HEALER] Could not read config: {e}")
        
        return config
    
    def _get_dependency_info(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Get information about installed dependencies."""
        if self._dependency_cache:
            return self._dependency_cache
        
        try:
            # Try to read requirements.txt
            req_file = self.repo_path / "requirements.txt"
            if req_file.exists():
                with open(req_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '==' in line:
                            parts = line.split('==')
                            if len(parts) == 2:
                                self._dependency_cache[parts[0].strip()] = parts[1].strip()
        except Exception as e:
            logger.debug(f"[CONFIG-HEALER] Could not read dependency info: {e}")
        
        return self._dependency_cache
    
    def apply_fix(
        self,
        error: ConfigError,
        auto_apply: bool = False
    ) -> Tuple[bool, str]:
        """
        Apply configuration fix.
        
        Args:
            error: ConfigError with suggested fix
            auto_apply: Whether to automatically apply the fix
            
        Returns:
            Tuple of (success, message)
        """
        if not error.suggested_value:
            return False, "No suggested value available"
        
        # Determine config file location
        config_file = error.config_file or self._find_config_file(error.config_key)
        
        if not config_file:
            return False, f"Could not determine config file for {error.config_key}"
        
        if not auto_apply:
            return True, f"Suggested fix: Set {error.config_key}={error.suggested_value} in {config_file}"
        
        # Apply fix
        try:
            if config_file.endswith('.env'):
                return self._fix_env_file(config_file, error)
            elif 'settings.py' in config_file:
                return self._fix_settings_py(config_file, error)
            else:
                return False, f"Unsupported config file format: {config_file}"
        except Exception as e:
            return False, f"Error applying fix: {e}"
    
    def _find_config_file(self, config_key: Optional[str] = None) -> Optional[str]:
        """Find the appropriate config file for a key."""
        # Check for .env file
        env_file = self.repo_path / "backend" / ".env"
        if env_file.exists():
            return str(env_file)
        
        # Check for settings.py
        settings_file = self.repo_path / "backend" / "settings.py"
        if settings_file.exists():
            return str(settings_file)
        
        return None
    
    def _fix_env_file(self, env_file: str, error: ConfigError) -> Tuple[bool, str]:
        """Fix .env file."""
        try:
            env_path = Path(env_file)
            
            # Read current .env
            lines = []
            key_found = False
            
            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            # Update or add the key
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{error.config_key}="):
                    # Update existing line
                    lines[i] = f"{error.config_key}={error.suggested_value}\n"
                    key_found = True
                    break
            
            if not key_found:
                # Add new line
                lines.append(f"{error.config_key}={error.suggested_value}\n")
            
            # Write back
            with open(env_path, 'w') as f:
                f.writelines(lines)
            
            return True, f"Updated {error.config_key} in {env_file}"
            
        except Exception as e:
            return False, f"Error fixing .env file: {e}"
    
    def _fix_settings_py(self, settings_file: str, error: ConfigError) -> Tuple[bool, str]:
        """Fix settings.py file (more complex - would need AST manipulation)."""
        # For now, just return suggestion
        # Could be enhanced with AST manipulation for automatic fixes
        return False, f"Manual fix required: Update {error.config_key} in {settings_file}"


def get_config_healer(llm_service=None, repo_path: Optional[Path] = None) -> LLMConfigHealer:
    """Get or create LLM Config Healer instance."""
    global _config_healer_instance
    
    if '_config_healer_instance' not in globals():
        _config_healer_instance = None
        
    if _config_healer_instance is None:
        _config_healer_instance = LLMConfigHealer(llm_service=llm_service, repo_path=repo_path)
        
    return _config_healer_instance
