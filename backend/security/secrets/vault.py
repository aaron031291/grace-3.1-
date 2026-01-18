"""
GRACE Secrets Vault - Multi-Backend Secrets Management

Provides enterprise-grade secrets management with:
- Multiple backend support (Local, HashiCorp Vault, AWS, Azure)
- Automatic failover between backends
- Secret caching with TTL
- Version management
- Audit logging for all access
- Self-healing on retrieval failures
"""

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SecretsError(Exception):
    """Base secrets error."""
    pass


class SecretNotFoundError(SecretsError):
    """Secret not found."""
    pass


class SecretAccessDeniedError(SecretsError):
    """Access to secret denied."""
    pass


class BackendUnavailableError(SecretsError):
    """Backend is unavailable."""
    pass


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    name: str
    version: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    rotation_enabled: bool = False
    tags: Dict[str, str] = field(default_factory=dict)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "rotation_enabled": self.rotation_enabled,
            "tags": self.tags,
            "custom_metadata": self.custom_metadata,
        }


@dataclass
class SecretEntry:
    """A secret entry with value and metadata."""
    name: str
    value: str
    metadata: SecretMetadata
    backend: str = "unknown"
    
    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "metadata": self.metadata.to_dict(),
            "backend": self.backend,
        }
        if include_value:
            result["value"] = self.value
        return result


@dataclass
class CachedSecret:
    """Cached secret with expiration."""
    entry: SecretEntry
    cached_at: datetime
    ttl: timedelta
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.cached_at + self.ttl


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available."""
        pass
    
    @abstractmethod
    def get_secret(self, name: str, version: Optional[str] = None) -> SecretEntry:
        """Get a secret by name."""
        pass
    
    @abstractmethod
    def set_secret(
        self,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretMetadata:
        """Store a secret."""
        pass
    
    @abstractmethod
    def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        """List secret names."""
        pass
    
    @abstractmethod
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get secret metadata without value."""
        pass


class LocalEncryptedBackend(SecretsBackend):
    """
    Local encrypted file storage backend.
    
    Stores secrets in encrypted JSON files using AES-256-GCM.
    Suitable for development and small deployments.
    """
    
    def __init__(
        self,
        storage_path: str = "data/secrets",
        encryption_key: Optional[bytes] = None,
        master_password: Optional[str] = None,
    ):
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.RLock()
        self._secrets: Dict[str, Dict[str, Any]] = {}
        self._encryption = None
        
        # Initialize encryption
        try:
            from .encryption import AESGCMEncryption, KeyDerivation
            
            if encryption_key:
                self._encryption = AESGCMEncryption(encryption_key)
            elif master_password:
                key, salt = KeyDerivation.derive_key(master_password)
                self._encryption = AESGCMEncryption(key)
                self._save_salt(salt)
            else:
                # Generate new key
                self._encryption = AESGCMEncryption()
                logger.warning("[SECRETS] Using auto-generated encryption key")
        except ImportError:
            logger.warning("[SECRETS] Encryption not available, storing plaintext")
        
        self._load_secrets()
        logger.info(f"[SECRETS] Local backend initialized at {self._storage_path}")
    
    @property
    def name(self) -> str:
        return "local_encrypted"
    
    @property
    def is_available(self) -> bool:
        return True
    
    def _save_salt(self, salt: bytes):
        """Save salt for key derivation."""
        salt_file = self._storage_path / ".salt"
        salt_file.write_bytes(salt)
    
    def _get_secrets_file(self) -> Path:
        return self._storage_path / "secrets.enc"
    
    def _load_secrets(self):
        """Load secrets from encrypted file."""
        secrets_file = self._get_secrets_file()
        if not secrets_file.exists():
            self._secrets = {}
            return
        
        try:
            data = secrets_file.read_bytes()
            if self._encryption:
                from .encryption import EncryptedData
                encrypted = EncryptedData.from_bytes(data)
                decrypted = self._encryption.decrypt(encrypted)
                self._secrets = json.loads(decrypted.decode("utf-8"))
            else:
                self._secrets = json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"[SECRETS] Failed to load secrets: {e}")
            self._secrets = {}
    
    def _save_secrets(self):
        """Save secrets to encrypted file."""
        secrets_file = self._get_secrets_file()
        
        try:
            data = json.dumps(self._secrets, indent=2)
            if self._encryption:
                encrypted = self._encryption.encrypt(data)
                secrets_file.write_bytes(encrypted.to_bytes())
            else:
                secrets_file.write_text(data)
        except Exception as e:
            logger.error(f"[SECRETS] Failed to save secrets: {e}")
            raise SecretsError(f"Failed to save secrets: {e}")
    
    def get_secret(self, name: str, version: Optional[str] = None) -> SecretEntry:
        with self._lock:
            if name not in self._secrets:
                raise SecretNotFoundError(f"Secret not found: {name}")
            
            secret_data = self._secrets[name]
            
            # Get specific version or current
            if version:
                versions = secret_data.get("versions", {})
                if version not in versions:
                    raise SecretNotFoundError(f"Version not found: {name}@{version}")
                value = versions[version]["value"]
            else:
                value = secret_data["value"]
            
            metadata = SecretMetadata(
                name=name,
                version=secret_data.get("version", "v1"),
                created_at=datetime.fromisoformat(secret_data.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(secret_data.get("updated_at", datetime.utcnow().isoformat())),
                expires_at=datetime.fromisoformat(secret_data["expires_at"]) if secret_data.get("expires_at") else None,
                last_rotated=datetime.fromisoformat(secret_data["last_rotated"]) if secret_data.get("last_rotated") else None,
                rotation_enabled=secret_data.get("rotation_enabled", False),
                tags=secret_data.get("tags", {}),
                custom_metadata=secret_data.get("custom_metadata", {}),
            )
            
            return SecretEntry(
                name=name,
                value=value,
                metadata=metadata,
                backend=self.name,
            )
    
    def set_secret(
        self,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretMetadata:
        with self._lock:
            now = datetime.utcnow()
            metadata = metadata or {}
            
            if name in self._secrets:
                # Update existing
                existing = self._secrets[name]
                old_version = existing.get("version", "v1")
                new_version = self._increment_version(old_version)
                
                # Save old version
                versions = existing.get("versions", {})
                versions[old_version] = {
                    "value": existing["value"],
                    "created_at": existing.get("updated_at", now.isoformat()),
                }
                
                existing["value"] = value
                existing["version"] = new_version
                existing["updated_at"] = now.isoformat()
                existing["versions"] = versions
                existing.update(metadata)
            else:
                # Create new
                new_version = "v1"
                self._secrets[name] = {
                    "value": value,
                    "version": new_version,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "versions": {},
                    **metadata,
                }
            
            self._save_secrets()
            
            return SecretMetadata(
                name=name,
                version=new_version,
                created_at=datetime.fromisoformat(self._secrets[name]["created_at"]),
                updated_at=now,
                tags=metadata.get("tags", {}),
            )
    
    def delete_secret(self, name: str) -> bool:
        with self._lock:
            if name not in self._secrets:
                return False
            del self._secrets[name]
            self._save_secrets()
            return True
    
    def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        with self._lock:
            names = list(self._secrets.keys())
            if prefix:
                names = [n for n in names if n.startswith(prefix)]
            return names
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        with self._lock:
            if name not in self._secrets:
                return None
            
            secret_data = self._secrets[name]
            return SecretMetadata(
                name=name,
                version=secret_data.get("version", "v1"),
                created_at=datetime.fromisoformat(secret_data.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(secret_data.get("updated_at", datetime.utcnow().isoformat())),
                expires_at=datetime.fromisoformat(secret_data["expires_at"]) if secret_data.get("expires_at") else None,
                last_rotated=datetime.fromisoformat(secret_data["last_rotated"]) if secret_data.get("last_rotated") else None,
                rotation_enabled=secret_data.get("rotation_enabled", False),
                tags=secret_data.get("tags", {}),
            )
    
    def _increment_version(self, version: str) -> str:
        """Increment version string (v1 -> v2)."""
        try:
            num = int(version[1:])
            return f"v{num + 1}"
        except (ValueError, IndexError):
            return "v1"


class HashiCorpVaultBackend(SecretsBackend):
    """
    HashiCorp Vault backend integration.
    
    Connects to HashiCorp Vault for enterprise secrets management.
    """
    
    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        vault_namespace: Optional[str] = None,
        mount_point: str = "secret",
    ):
        self._vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "http://localhost:8200")
        self._vault_token = vault_token or os.environ.get("VAULT_TOKEN")
        self._vault_namespace = vault_namespace or os.environ.get("VAULT_NAMESPACE")
        self._mount_point = mount_point
        self._client = None
        self._available = False
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Vault client."""
        try:
            import hvac
            
            self._client = hvac.Client(
                url=self._vault_addr,
                token=self._vault_token,
                namespace=self._vault_namespace,
            )
            
            if self._client.is_authenticated():
                self._available = True
                logger.info(f"[SECRETS] HashiCorp Vault connected at {self._vault_addr}")
            else:
                logger.warning("[SECRETS] HashiCorp Vault authentication failed")
                self._available = False
                
        except ImportError:
            logger.warning("[SECRETS] hvac library not installed, Vault backend unavailable")
            self._available = False
        except Exception as e:
            logger.warning(f"[SECRETS] HashiCorp Vault connection failed: {e}")
            self._available = False
    
    @property
    def name(self) -> str:
        return "hashicorp_vault"
    
    @property
    def is_available(self) -> bool:
        return self._available and self._client is not None
    
    def get_secret(self, name: str, version: Optional[str] = None) -> SecretEntry:
        if not self.is_available:
            raise BackendUnavailableError("HashiCorp Vault not available")
        
        try:
            if version:
                response = self._client.secrets.kv.v2.read_secret_version(
                    path=name,
                    version=int(version.replace("v", "")),
                    mount_point=self._mount_point,
                )
            else:
                response = self._client.secrets.kv.v2.read_secret_version(
                    path=name,
                    mount_point=self._mount_point,
                )
            
            data = response["data"]["data"]
            vault_metadata = response["data"]["metadata"]
            
            return SecretEntry(
                name=name,
                value=data.get("value", json.dumps(data)),
                metadata=SecretMetadata(
                    name=name,
                    version=f"v{vault_metadata['version']}",
                    created_at=datetime.fromisoformat(vault_metadata["created_time"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(vault_metadata["created_time"].replace("Z", "+00:00")),
                ),
                backend=self.name,
            )
        except Exception as e:
            if "InvalidPath" in str(e) or "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found: {name}")
            raise SecretsError(f"Failed to get secret: {e}")
    
    def set_secret(
        self,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretMetadata:
        if not self.is_available:
            raise BackendUnavailableError("HashiCorp Vault not available")
        
        try:
            response = self._client.secrets.kv.v2.create_or_update_secret(
                path=name,
                secret={"value": value, **(metadata or {})},
                mount_point=self._mount_point,
            )
            
            version = response["data"]["version"]
            now = datetime.utcnow()
            
            return SecretMetadata(
                name=name,
                version=f"v{version}",
                created_at=now,
                updated_at=now,
            )
        except Exception as e:
            raise SecretsError(f"Failed to set secret: {e}")
    
    def delete_secret(self, name: str) -> bool:
        if not self.is_available:
            raise BackendUnavailableError("HashiCorp Vault not available")
        
        try:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=name,
                mount_point=self._mount_point,
            )
            return True
        except Exception as e:
            logger.error(f"[SECRETS] Failed to delete secret: {e}")
            return False
    
    def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        if not self.is_available:
            raise BackendUnavailableError("HashiCorp Vault not available")
        
        try:
            path = prefix or ""
            response = self._client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self._mount_point,
            )
            return response["data"]["keys"]
        except Exception:
            return []
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        if not self.is_available:
            return None
        
        try:
            response = self._client.secrets.kv.v2.read_secret_metadata(
                path=name,
                mount_point=self._mount_point,
            )
            
            data = response["data"]
            return SecretMetadata(
                name=name,
                version=f"v{data['current_version']}",
                created_at=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(data["updated_time"].replace("Z", "+00:00")),
            )
        except Exception:
            return None


class AWSSecretsBackend(SecretsBackend):
    """
    AWS Secrets Manager backend integration.
    """
    
    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self._region = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self._client = None
        self._available = False
        
        self._initialize_client(aws_access_key_id, aws_secret_access_key)
    
    def _initialize_client(
        self,
        access_key: Optional[str],
        secret_key: Optional[str],
    ):
        try:
            import boto3
            
            kwargs = {"region_name": self._region}
            if access_key and secret_key:
                kwargs["aws_access_key_id"] = access_key
                kwargs["aws_secret_access_key"] = secret_key
            
            self._client = boto3.client("secretsmanager", **kwargs)
            
            # Test connection
            self._client.list_secrets(MaxResults=1)
            self._available = True
            logger.info(f"[SECRETS] AWS Secrets Manager connected in {self._region}")
            
        except ImportError:
            logger.warning("[SECRETS] boto3 library not installed, AWS backend unavailable")
        except Exception as e:
            logger.warning(f"[SECRETS] AWS Secrets Manager connection failed: {e}")
    
    @property
    def name(self) -> str:
        return "aws_secrets_manager"
    
    @property
    def is_available(self) -> bool:
        return self._available and self._client is not None
    
    def get_secret(self, name: str, version: Optional[str] = None) -> SecretEntry:
        if not self.is_available:
            raise BackendUnavailableError("AWS Secrets Manager not available")
        
        try:
            kwargs = {"SecretId": name}
            if version:
                kwargs["VersionId"] = version
            
            response = self._client.get_secret_value(**kwargs)
            
            value = response.get("SecretString", "")
            
            return SecretEntry(
                name=name,
                value=value,
                metadata=SecretMetadata(
                    name=name,
                    version=response.get("VersionId", "v1"),
                    created_at=response.get("CreatedDate", datetime.utcnow()),
                    updated_at=response.get("CreatedDate", datetime.utcnow()),
                ),
                backend=self.name,
            )
        except self._client.exceptions.ResourceNotFoundException:
            raise SecretNotFoundError(f"Secret not found: {name}")
        except Exception as e:
            raise SecretsError(f"Failed to get secret: {e}")
    
    def set_secret(
        self,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretMetadata:
        if not self.is_available:
            raise BackendUnavailableError("AWS Secrets Manager not available")
        
        try:
            # Try to update existing
            try:
                response = self._client.put_secret_value(
                    SecretId=name,
                    SecretString=value,
                )
            except self._client.exceptions.ResourceNotFoundException:
                # Create new
                response = self._client.create_secret(
                    Name=name,
                    SecretString=value,
                    Tags=[{"Key": k, "Value": v} for k, v in (metadata or {}).get("tags", {}).items()],
                )
            
            now = datetime.utcnow()
            return SecretMetadata(
                name=name,
                version=response.get("VersionId", "v1"),
                created_at=now,
                updated_at=now,
            )
        except Exception as e:
            raise SecretsError(f"Failed to set secret: {e}")
    
    def delete_secret(self, name: str) -> bool:
        if not self.is_available:
            raise BackendUnavailableError("AWS Secrets Manager not available")
        
        try:
            self._client.delete_secret(
                SecretId=name,
                ForceDeleteWithoutRecovery=True,
            )
            return True
        except Exception:
            return False
    
    def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        if not self.is_available:
            return []
        
        try:
            secrets = []
            paginator = self._client.get_paginator("list_secrets")
            
            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    name = secret["Name"]
                    if prefix is None or name.startswith(prefix):
                        secrets.append(name)
            
            return secrets
        except Exception:
            return []
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        if not self.is_available:
            return None
        
        try:
            response = self._client.describe_secret(SecretId=name)
            return SecretMetadata(
                name=name,
                version=list(response.get("VersionIdsToStages", {}).keys())[0] if response.get("VersionIdsToStages") else "v1",
                created_at=response.get("CreatedDate", datetime.utcnow()),
                updated_at=response.get("LastChangedDate", datetime.utcnow()),
                last_rotated=response.get("LastRotatedDate"),
                rotation_enabled=response.get("RotationEnabled", False),
            )
        except Exception:
            return None


class AzureKeyVaultBackend(SecretsBackend):
    """
    Azure Key Vault backend integration.
    """
    
    def __init__(
        self,
        vault_url: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self._vault_url = vault_url or os.environ.get("AZURE_VAULT_URL")
        self._client = None
        self._available = False
        
        if self._vault_url:
            self._initialize_client(tenant_id, client_id, client_secret)
    
    def _initialize_client(
        self,
        tenant_id: Optional[str],
        client_id: Optional[str],
        client_secret: Optional[str],
    ):
        try:
            from azure.identity import DefaultAzureCredential, ClientSecretCredential
            from azure.keyvault.secrets import SecretClient
            
            if client_id and client_secret and tenant_id:
                credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            else:
                credential = DefaultAzureCredential()
            
            self._client = SecretClient(vault_url=self._vault_url, credential=credential)
            
            # Test connection
            list(self._client.list_properties_of_secrets(max_page_size=1))
            self._available = True
            logger.info(f"[SECRETS] Azure Key Vault connected at {self._vault_url}")
            
        except ImportError:
            logger.warning("[SECRETS] Azure SDK not installed, Azure backend unavailable")
        except Exception as e:
            logger.warning(f"[SECRETS] Azure Key Vault connection failed: {e}")
    
    @property
    def name(self) -> str:
        return "azure_key_vault"
    
    @property
    def is_available(self) -> bool:
        return self._available and self._client is not None
    
    def get_secret(self, name: str, version: Optional[str] = None) -> SecretEntry:
        if not self.is_available:
            raise BackendUnavailableError("Azure Key Vault not available")
        
        try:
            secret = self._client.get_secret(name, version=version)
            
            return SecretEntry(
                name=name,
                value=secret.value,
                metadata=SecretMetadata(
                    name=name,
                    version=secret.properties.version or "v1",
                    created_at=secret.properties.created_on or datetime.utcnow(),
                    updated_at=secret.properties.updated_on or datetime.utcnow(),
                    expires_at=secret.properties.expires_on,
                    tags=secret.properties.tags or {},
                ),
                backend=self.name,
            )
        except Exception as e:
            if "not found" in str(e).lower():
                raise SecretNotFoundError(f"Secret not found: {name}")
            raise SecretsError(f"Failed to get secret: {e}")
    
    def set_secret(
        self,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretMetadata:
        if not self.is_available:
            raise BackendUnavailableError("Azure Key Vault not available")
        
        try:
            secret = self._client.set_secret(
                name,
                value,
                tags=metadata.get("tags") if metadata else None,
            )
            
            return SecretMetadata(
                name=name,
                version=secret.properties.version or "v1",
                created_at=secret.properties.created_on or datetime.utcnow(),
                updated_at=secret.properties.updated_on or datetime.utcnow(),
            )
        except Exception as e:
            raise SecretsError(f"Failed to set secret: {e}")
    
    def delete_secret(self, name: str) -> bool:
        if not self.is_available:
            return False
        
        try:
            poller = self._client.begin_delete_secret(name)
            poller.result()
            return True
        except Exception:
            return False
    
    def list_secrets(self, prefix: Optional[str] = None) -> List[str]:
        if not self.is_available:
            return []
        
        try:
            secrets = []
            for props in self._client.list_properties_of_secrets():
                if prefix is None or props.name.startswith(prefix):
                    secrets.append(props.name)
            return secrets
        except Exception:
            return []
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        if not self.is_available:
            return None
        
        try:
            secret = self._client.get_secret(name)
            return SecretMetadata(
                name=name,
                version=secret.properties.version or "v1",
                created_at=secret.properties.created_on or datetime.utcnow(),
                updated_at=secret.properties.updated_on or datetime.utcnow(),
                expires_at=secret.properties.expires_on,
                tags=secret.properties.tags or {},
            )
        except Exception:
            return None


class SecretsVault:
    """
    Main secrets vault with multi-backend support.
    
    Features:
    - Multiple backend fallback chain
    - Secret caching with TTL
    - Audit logging
    - Self-healing on failures
    """
    
    def __init__(
        self,
        backends: Optional[List[SecretsBackend]] = None,
        cache_ttl: timedelta = timedelta(minutes=5),
        enable_audit: bool = True,
    ):
        self._backends: List[SecretsBackend] = backends or []
        self._cache_ttl = cache_ttl
        self._enable_audit = enable_audit
        
        self._cache: Dict[str, CachedSecret] = {}
        self._cache_lock = threading.RLock()
        
        self._retry_count = 3
        self._retry_delay = 0.5
        
        if not self._backends:
            # Default to local backend
            self._backends = [LocalEncryptedBackend()]
        
        logger.info(f"[SECRETS] Vault initialized with {len(self._backends)} backends")
    
    def add_backend(self, backend: SecretsBackend, priority: int = -1):
        """Add a backend to the vault."""
        if priority < 0 or priority >= len(self._backends):
            self._backends.append(backend)
        else:
            self._backends.insert(priority, backend)
        logger.info(f"[SECRETS] Added backend: {backend.name}")
    
    def get(
        self,
        name: str,
        version: Optional[str] = None,
        use_cache: bool = True,
    ) -> str:
        """
        Get a secret value.
        
        Args:
            name: Secret name
            version: Optional version
            use_cache: Whether to use cache
            
        Returns:
            Secret value
        """
        cache_key = f"{name}:{version or 'latest'}"
        
        # Check cache
        if use_cache:
            with self._cache_lock:
                if cache_key in self._cache:
                    cached = self._cache[cache_key]
                    if not cached.is_expired:
                        self._audit_access(name, "cache_hit")
                        return cached.entry.value
        
        # Try backends with fallback
        last_error = None
        for backend in self._backends:
            if not backend.is_available:
                continue
            
            for attempt in range(self._retry_count):
                try:
                    entry = backend.get_secret(name, version)
                    
                    # Update cache
                    with self._cache_lock:
                        self._cache[cache_key] = CachedSecret(
                            entry=entry,
                            cached_at=datetime.utcnow(),
                            ttl=self._cache_ttl,
                        )
                    
                    self._audit_access(name, "retrieved", backend.name)
                    return entry.value
                    
                except SecretNotFoundError:
                    raise
                except Exception as e:
                    last_error = e
                    if attempt < self._retry_count - 1:
                        time.sleep(self._retry_delay * (attempt + 1))
                    continue
        
        self._audit_access(name, "failed", error=str(last_error))
        raise SecretsError(f"Failed to get secret from all backends: {last_error}")
    
    def set(
        self,
        name: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretMetadata:
        """
        Store a secret.
        
        Args:
            name: Secret name
            value: Secret value
            metadata: Optional metadata
            
        Returns:
            Secret metadata
        """
        last_error = None
        
        for backend in self._backends:
            if not backend.is_available:
                continue
            
            try:
                result = backend.set_secret(name, value, metadata)
                
                # Invalidate cache
                with self._cache_lock:
                    keys_to_remove = [k for k in self._cache if k.startswith(f"{name}:")]
                    for key in keys_to_remove:
                        del self._cache[key]
                
                self._audit_access(name, "stored", backend.name)
                return result
                
            except Exception as e:
                last_error = e
                continue
        
        self._audit_access(name, "store_failed", error=str(last_error))
        raise SecretsError(f"Failed to store secret in all backends: {last_error}")
    
    def delete(self, name: str) -> bool:
        """Delete a secret from all backends."""
        deleted = False
        
        for backend in self._backends:
            if not backend.is_available:
                continue
            
            try:
                if backend.delete_secret(name):
                    deleted = True
            except Exception as e:
                logger.warning(f"[SECRETS] Delete failed on {backend.name}: {e}")
        
        # Clear cache
        with self._cache_lock:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{name}:")]
            for key in keys_to_remove:
                del self._cache[key]
        
        if deleted:
            self._audit_access(name, "deleted")
        
        return deleted
    
    def list(self, prefix: Optional[str] = None) -> List[str]:
        """List all secret names."""
        all_secrets = set()
        
        for backend in self._backends:
            if not backend.is_available:
                continue
            
            try:
                secrets = backend.list_secrets(prefix)
                all_secrets.update(secrets)
            except Exception as e:
                logger.warning(f"[SECRETS] List failed on {backend.name}: {e}")
        
        return sorted(list(all_secrets))
    
    def get_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get secret metadata."""
        for backend in self._backends:
            if not backend.is_available:
                continue
            
            try:
                metadata = backend.get_metadata(name)
                if metadata:
                    return metadata
            except Exception:
                continue
        
        return None
    
    def rotate(
        self,
        name: str,
        new_value: Optional[str] = None,
        generator: Optional[Callable[[], str]] = None,
    ) -> SecretMetadata:
        """
        Rotate a secret.
        
        Args:
            name: Secret name
            new_value: New value (generated if not provided)
            generator: Value generator function
            
        Returns:
            Updated metadata
        """
        if new_value is None:
            if generator:
                new_value = generator()
            else:
                # Default: generate 32-byte random value
                import secrets as std_secrets
                new_value = std_secrets.token_urlsafe(32)
        
        metadata = self.set(name, new_value, {"last_rotated": datetime.utcnow().isoformat()})
        self._audit_access(name, "rotated")
        
        return metadata
    
    def clear_cache(self):
        """Clear the entire cache."""
        with self._cache_lock:
            self._cache.clear()
    
    def _audit_access(
        self,
        secret_name: str,
        action: str,
        backend: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Audit secret access."""
        if not self._enable_audit:
            return
        
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.DATA_ACCESS,
                    action_description=f"Secret {action}: {secret_name}",
                    actor_type="system",
                    actor_id="secrets_vault",
                    component="secrets",
                    severity="info" if not error else "warning",
                    context={
                        "secret_name": secret_name,
                        "action": action,
                        "backend": backend,
                        "error": error,
                    },
                )
        except Exception as e:
            logger.debug(f"[SECRETS] Audit logging failed: {e}")


# Singleton
_vault: Optional[SecretsVault] = None


def get_secrets_vault() -> SecretsVault:
    """Get the secrets vault singleton."""
    global _vault
    if _vault is None:
        from .config import get_secrets_config
        
        config = get_secrets_config()
        backends = []
        
        # Initialize configured backends
        if config.local_enabled:
            backends.append(LocalEncryptedBackend(
                storage_path=config.local_storage_path,
                master_password=config.local_master_password,
            ))
        
        if config.hashicorp_enabled:
            backends.append(HashiCorpVaultBackend(
                vault_addr=config.hashicorp_addr,
                vault_token=config.hashicorp_token,
            ))
        
        if config.aws_enabled:
            backends.append(AWSSecretsBackend(
                region_name=config.aws_region,
            ))
        
        if config.azure_enabled:
            backends.append(AzureKeyVaultBackend(
                vault_url=config.azure_vault_url,
            ))
        
        _vault = SecretsVault(
            backends=backends,
            cache_ttl=timedelta(seconds=config.cache_ttl_seconds),
            enable_audit=config.enable_audit,
        )
    
    return _vault
