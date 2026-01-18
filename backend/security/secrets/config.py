"""
Secrets Management Configuration for GRACE

Environment-based configuration for the enterprise secrets system.
Provides validation of required secrets on startup and health checks.
"""

import os
import logging
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta

logger = logging.getLogger(__name__)


class SecretBackendType(str, Enum):
    """Supported secret backend types."""
    LOCAL = "local"
    HASHICORP_VAULT = "hashicorp_vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"
    ENVIRONMENT = "environment"


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"


class KeyDerivationFunction(str, Enum):
    """Supported key derivation functions."""
    ARGON2ID = "argon2id"
    ARGON2I = "argon2i"
    PBKDF2_SHA256 = "pbkdf2-sha256"
    SCRYPT = "scrypt"


@dataclass
class RotationPolicy:
    """Secret rotation policy configuration."""
    enabled: bool = True
    interval: timedelta = field(default_factory=lambda: timedelta(days=90))
    grace_period: timedelta = field(default_factory=lambda: timedelta(hours=24))
    max_versions: int = 5
    auto_rollback: bool = True
    notify_before: timedelta = field(default_factory=lambda: timedelta(days=7))


@dataclass
class CacheConfig:
    """Secret cache configuration."""
    enabled: bool = True
    ttl: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    max_size: int = 1000
    refresh_ahead: bool = True
    refresh_threshold: float = 0.75


@dataclass
class VaultConfig:
    """HashiCorp Vault configuration."""
    address: str = ""
    token: str = ""
    namespace: str = ""
    mount_path: str = "secret"
    kv_version: int = 2
    tls_verify: bool = True
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class AWSSecretsConfig:
    """AWS Secrets Manager configuration."""
    region: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""
    session_token: str = ""
    endpoint_url: Optional[str] = None
    use_iam_role: bool = True


@dataclass
class AzureKeyVaultConfig:
    """Azure Key Vault configuration."""
    vault_url: str = ""
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    use_managed_identity: bool = True


@dataclass
class LocalStorageConfig:
    """Local encrypted storage configuration."""
    storage_path: str = ""
    master_key_path: str = ""
    encryption_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_derivation: KeyDerivationFunction = KeyDerivationFunction.ARGON2ID


@dataclass 
class HSMConfig:
    """Hardware Security Module configuration."""
    enabled: bool = False
    provider: str = "pkcs11"
    library_path: str = ""
    slot_id: int = 0
    pin: str = ""
    key_label: str = "grace-master-key"


@dataclass
class SecretsConfig:
    """
    Main secrets management configuration.
    
    Loaded from environment variables with sensible defaults.
    """
    
    primary_backend: SecretBackendType = SecretBackendType.ENVIRONMENT
    fallback_backends: List[SecretBackendType] = field(default_factory=list)
    
    vault: VaultConfig = field(default_factory=VaultConfig)
    aws: AWSSecretsConfig = field(default_factory=AWSSecretsConfig)
    azure: AzureKeyVaultConfig = field(default_factory=AzureKeyVaultConfig)
    local: LocalStorageConfig = field(default_factory=LocalStorageConfig)
    hsm: HSMConfig = field(default_factory=HSMConfig)
    
    cache: CacheConfig = field(default_factory=CacheConfig)
    default_rotation: RotationPolicy = field(default_factory=RotationPolicy)
    
    audit_enabled: bool = True
    audit_include_values: bool = False
    
    required_secrets: Set[str] = field(default_factory=set)
    
    self_healing_enabled: bool = True
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: int = 60
    
    def __post_init__(self):
        """Load configuration from environment variables."""
        self._load_from_env()
    
    def _load_from_env(self):
        """Load all configuration from environment."""
        self.primary_backend = SecretBackendType(
            os.getenv("SECRETS_PRIMARY_BACKEND", "environment")
        )
        
        fallback = os.getenv("SECRETS_FALLBACK_BACKENDS", "")
        if fallback:
            self.fallback_backends = [
                SecretBackendType(b.strip()) 
                for b in fallback.split(",")
            ]
        
        self.vault.address = os.getenv("VAULT_ADDR", "")
        self.vault.token = os.getenv("VAULT_TOKEN", "")
        self.vault.namespace = os.getenv("VAULT_NAMESPACE", "")
        self.vault.mount_path = os.getenv("VAULT_MOUNT_PATH", "secret")
        self.vault.kv_version = int(os.getenv("VAULT_KV_VERSION", "2"))
        self.vault.tls_verify = os.getenv("VAULT_TLS_VERIFY", "true").lower() == "true"
        self.vault.ca_cert_path = os.getenv("VAULT_CA_CERT") or None
        self.vault.timeout = int(os.getenv("VAULT_TIMEOUT", "30"))
        
        self.aws.region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", ""))
        self.aws.access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.aws.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.aws.session_token = os.getenv("AWS_SESSION_TOKEN", "")
        self.aws.endpoint_url = os.getenv("AWS_SECRETS_ENDPOINT_URL") or None
        self.aws.use_iam_role = os.getenv("AWS_USE_IAM_ROLE", "true").lower() == "true"
        
        self.azure.vault_url = os.getenv("AZURE_KEY_VAULT_URL", "")
        self.azure.tenant_id = os.getenv("AZURE_TENANT_ID", "")
        self.azure.client_id = os.getenv("AZURE_CLIENT_ID", "")
        self.azure.client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
        self.azure.use_managed_identity = os.getenv(
            "AZURE_USE_MANAGED_IDENTITY", "true"
        ).lower() == "true"
        
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        default_storage = os.path.join(backend_dir, "data", "secrets")
        self.local.storage_path = os.getenv("SECRETS_LOCAL_PATH", default_storage)
        self.local.master_key_path = os.getenv(
            "SECRETS_MASTER_KEY_PATH", 
            os.path.join(default_storage, ".master.key")
        )
        
        self.hsm.enabled = os.getenv("HSM_ENABLED", "false").lower() == "true"
        self.hsm.library_path = os.getenv("HSM_LIBRARY_PATH", "")
        self.hsm.slot_id = int(os.getenv("HSM_SLOT_ID", "0"))
        self.hsm.pin = os.getenv("HSM_PIN", "")
        self.hsm.key_label = os.getenv("HSM_KEY_LABEL", "grace-master-key")
        
        self.cache.enabled = os.getenv("SECRETS_CACHE_ENABLED", "true").lower() == "true"
        cache_ttl = int(os.getenv("SECRETS_CACHE_TTL_SECONDS", "300"))
        self.cache.ttl = timedelta(seconds=cache_ttl)
        self.cache.max_size = int(os.getenv("SECRETS_CACHE_MAX_SIZE", "1000"))
        
        self.audit_enabled = os.getenv("SECRETS_AUDIT_ENABLED", "true").lower() == "true"
        self.audit_include_values = os.getenv(
            "SECRETS_AUDIT_INCLUDE_VALUES", "false"
        ).lower() == "true"
        
        required = os.getenv("SECRETS_REQUIRED", "")
        if required:
            self.required_secrets = set(s.strip() for s in required.split(","))
        
        self.self_healing_enabled = os.getenv(
            "SECRETS_SELF_HEALING", "true"
        ).lower() == "true"
        self.max_retry_attempts = int(os.getenv("SECRETS_MAX_RETRIES", "3"))
        self.retry_delay_seconds = float(os.getenv("SECRETS_RETRY_DELAY", "1.0"))
    
    def validate_backend(self, backend: SecretBackendType) -> List[str]:
        """
        Validate that a backend is properly configured.
        
        Returns list of missing configuration items.
        """
        missing = []
        
        if backend == SecretBackendType.HASHICORP_VAULT:
            if not self.vault.address:
                missing.append("VAULT_ADDR")
            if not self.vault.token:
                missing.append("VAULT_TOKEN")
                
        elif backend == SecretBackendType.AWS_SECRETS_MANAGER:
            if not self.aws.region:
                missing.append("AWS_REGION")
            if not self.aws.use_iam_role:
                if not self.aws.access_key_id:
                    missing.append("AWS_ACCESS_KEY_ID")
                if not self.aws.secret_access_key:
                    missing.append("AWS_SECRET_ACCESS_KEY")
                    
        elif backend == SecretBackendType.AZURE_KEY_VAULT:
            if not self.azure.vault_url:
                missing.append("AZURE_KEY_VAULT_URL")
            if not self.azure.use_managed_identity:
                if not self.azure.tenant_id:
                    missing.append("AZURE_TENANT_ID")
                if not self.azure.client_id:
                    missing.append("AZURE_CLIENT_ID")
                if not self.azure.client_secret:
                    missing.append("AZURE_CLIENT_SECRET")
                    
        elif backend == SecretBackendType.LOCAL:
            if not self.local.storage_path:
                missing.append("SECRETS_LOCAL_PATH")
        
        return missing
    
    def get_available_backends(self) -> List[SecretBackendType]:
        """Get list of properly configured backends."""
        available = []
        for backend in SecretBackendType:
            if not self.validate_backend(backend):
                available.append(backend)
        return available


_secrets_config: Optional[SecretsConfig] = None


def get_secrets_config() -> SecretsConfig:
    """Get the secrets configuration singleton."""
    global _secrets_config
    if _secrets_config is None:
        _secrets_config = SecretsConfig()
    return _secrets_config


def reset_secrets_config():
    """Reset configuration (for testing)."""
    global _secrets_config
    _secrets_config = None


class SecretsHealthChecker:
    """Health checks for secret backends."""
    
    def __init__(self, config: Optional[SecretsConfig] = None):
        self.config = config or get_secrets_config()
        self._health_cache: Dict[SecretBackendType, Dict[str, Any]] = {}
    
    def check_backend_health(self, backend: SecretBackendType) -> Dict[str, Any]:
        """Check health of a specific backend."""
        result = {
            "backend": backend.value,
            "healthy": False,
            "latency_ms": None,
            "error": None,
            "details": {}
        }
        
        import time
        start = time.time()
        
        try:
            if backend == SecretBackendType.ENVIRONMENT:
                result["healthy"] = True
                result["details"]["source"] = "environment_variables"
                
            elif backend == SecretBackendType.HASHICORP_VAULT:
                result = self._check_vault_health(result)
                
            elif backend == SecretBackendType.AWS_SECRETS_MANAGER:
                result = self._check_aws_health(result)
                
            elif backend == SecretBackendType.AZURE_KEY_VAULT:
                result = self._check_azure_health(result)
                
            elif backend == SecretBackendType.LOCAL:
                result = self._check_local_health(result)
                
        except Exception as e:
            result["error"] = str(e)
            
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
        self._health_cache[backend] = result
        return result
    
    def _check_vault_health(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Check HashiCorp Vault health."""
        missing = self.config.validate_backend(SecretBackendType.HASHICORP_VAULT)
        if missing:
            result["error"] = f"Missing configuration: {', '.join(missing)}"
            return result
        
        try:
            import hvac
            client = hvac.Client(
                url=self.config.vault.address,
                token=self.config.vault.token,
                namespace=self.config.vault.namespace or None,
                verify=self.config.vault.tls_verify
            )
            health = client.sys.read_health_status(method='GET')
            result["healthy"] = not health.get("sealed", True)
            result["details"] = {
                "sealed": health.get("sealed"),
                "initialized": health.get("initialized"),
                "version": health.get("version")
            }
        except ImportError:
            result["error"] = "hvac library not installed"
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _check_aws_health(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Check AWS Secrets Manager health."""
        missing = self.config.validate_backend(SecretBackendType.AWS_SECRETS_MANAGER)
        if missing:
            result["error"] = f"Missing configuration: {', '.join(missing)}"
            return result
        
        try:
            import boto3
            client = boto3.client(
                'secretsmanager',
                region_name=self.config.aws.region,
                endpoint_url=self.config.aws.endpoint_url
            )
            client.list_secrets(MaxResults=1)
            result["healthy"] = True
            result["details"]["region"] = self.config.aws.region
        except ImportError:
            result["error"] = "boto3 library not installed"
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _check_azure_health(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Check Azure Key Vault health."""
        missing = self.config.validate_backend(SecretBackendType.AZURE_KEY_VAULT)
        if missing:
            result["error"] = f"Missing configuration: {', '.join(missing)}"
            return result
        
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultAzureCredential()
            client = SecretClient(
                vault_url=self.config.azure.vault_url,
                credential=credential
            )
            list(client.list_properties_of_secrets(max_page_size=1))
            result["healthy"] = True
            result["details"]["vault_url"] = self.config.azure.vault_url
        except ImportError:
            result["error"] = "azure-identity/azure-keyvault-secrets libraries not installed"
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _check_local_health(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Check local storage health."""
        import os
        storage_path = self.config.local.storage_path
        
        if not storage_path:
            result["error"] = "Storage path not configured"
            return result
        
        if os.path.exists(storage_path):
            result["healthy"] = True
            result["details"]["path"] = storage_path
            result["details"]["writable"] = os.access(storage_path, os.W_OK)
        else:
            try:
                os.makedirs(storage_path, exist_ok=True)
                result["healthy"] = True
                result["details"]["path"] = storage_path
                result["details"]["created"] = True
            except Exception as e:
                result["error"] = f"Cannot create storage: {e}"
                
        return result
    
    def check_all_backends(self) -> Dict[str, Any]:
        """Check health of all configured backends."""
        results = {}
        primary = self.config.primary_backend
        
        results["primary"] = self.check_backend_health(primary)
        results["fallbacks"] = [
            self.check_backend_health(backend)
            for backend in self.config.fallback_backends
        ]
        results["overall_healthy"] = results["primary"]["healthy"] or any(
            fb["healthy"] for fb in results["fallbacks"]
        )
        
        return results
    
    def validate_required_secrets(self, vault) -> Dict[str, Any]:
        """
        Validate that all required secrets are available.
        
        Args:
            vault: SecretsVault instance to check secrets
            
        Returns:
            Validation results with missing secrets
        """
        results = {
            "valid": True,
            "checked": [],
            "missing": [],
            "errors": []
        }
        
        for secret_name in self.config.required_secrets:
            results["checked"].append(secret_name)
            try:
                value = vault.get(secret_name)
                if value is None:
                    results["missing"].append(secret_name)
                    results["valid"] = False
            except Exception as e:
                results["errors"].append({
                    "secret": secret_name,
                    "error": str(e)
                })
                results["valid"] = False
        
        return results


def get_health_checker() -> SecretsHealthChecker:
    """Get a health checker instance."""
    return SecretsHealthChecker()
