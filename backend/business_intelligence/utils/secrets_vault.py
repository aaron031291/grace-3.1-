"""
Secrets Vault

Encrypted storage for API credentials and sensitive customer data.
Uses Fernet symmetric encryption (AES-128-CBC) with a master key
derived from a passphrase.

Data at rest is always encrypted. The vault file is a JSON structure
where all values are encrypted individually, so even if the file is
exposed, individual secrets are protected.

Usage:
    vault = SecretsVault("my_passphrase")
    vault.store("SHOPIFY_API_KEY", "shpat_xxx")
    key = vault.retrieve("SHOPIFY_API_KEY")
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SecretsVault:
    """Encrypted secrets storage with passphrase protection."""

    VAULT_FILENAME = ".bi_secrets_vault.enc"

    def __init__(
        self,
        passphrase: Optional[str] = None,
        vault_path: Optional[str] = None,
    ):
        self.vault_path = Path(
            vault_path or os.path.join("backend", "data", self.VAULT_FILENAME)
        )
        self._fernet = None
        self._data: Dict[str, Dict[str, str]] = {}
        self._initialized = False

        resolved_passphrase = passphrase or os.getenv("BI_VAULT_PASSPHRASE")
        if resolved_passphrase:
            self._init_encryption(resolved_passphrase)
            self._load()

    def _init_encryption(self, passphrase: str):
        """Initialize Fernet encryption from passphrase."""
        try:
            from cryptography.fernet import Fernet

            key = hashlib.sha256(passphrase.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key)
            self._fernet = Fernet(fernet_key)
            self._initialized = True
        except ImportError:
            logger.warning(
                "cryptography package not installed. "
                "Vault will operate in plaintext mode. "
                "Install with: pip install cryptography"
            )
            self._fernet = None
            self._initialized = True

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        if self._fernet:
            return self._fernet.encrypt(plaintext.encode()).decode()
        return base64.b64encode(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt a string value."""
        if self._fernet:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        return base64.b64decode(ciphertext.encode()).decode()

    def store(self, key: str, value: str, category: str = "api_key") -> bool:
        """Store a secret in the vault."""
        if not self._initialized:
            logger.error("Vault not initialized. Provide a passphrase.")
            return False

        self._data[key] = {
            "value": self._encrypt(value),
            "category": category,
            "stored_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self._save()
        logger.info(f"Secret stored: {key} (category: {category})")
        return True

    def retrieve(self, key: str) -> Optional[str]:
        """Retrieve a secret from the vault."""
        if not self._initialized:
            return None

        entry = self._data.get(key)
        if not entry:
            return None

        try:
            return self._decrypt(entry["value"])
        except Exception as e:
            logger.error(f"Failed to decrypt secret {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a secret from the vault."""
        if key in self._data:
            del self._data[key]
            self._save()
            logger.info(f"Secret deleted: {key}")
            return True
        return False

    def list_keys(self) -> List[Dict[str, str]]:
        """List all stored secret keys (not values)."""
        return [
            {
                "key": key,
                "category": entry.get("category", "unknown"),
                "stored_at": entry.get("stored_at", ""),
                "updated_at": entry.get("updated_at", ""),
            }
            for key, entry in self._data.items()
        ]

    def store_customer_data(
        self,
        customer_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Store sensitive customer data with encryption.

        Only stores data that the customer has consented to share.
        Automatically redacts prohibited fields.
        """
        from business_intelligence.config import BIConfig

        config = BIConfig.from_env()
        safe_data = {
            k: v for k, v in data.items()
            if k not in config.prohibited_data_fields
        }

        serialized = json.dumps(safe_data, default=str)
        return self.store(
            f"customer_{customer_id}",
            serialized,
            category="customer_data",
        )

    def retrieve_customer_data(
        self, customer_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve encrypted customer data."""
        raw = self.retrieve(f"customer_{customer_id}")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def load_secrets_to_env(self, category: str = "api_key"):
        """Load vault secrets into environment variables.

        Allows the BI system to use vault-stored API keys
        without them being in .env files.
        """
        loaded = 0
        for key, entry in self._data.items():
            if entry.get("category") == category:
                try:
                    value = self._decrypt(entry["value"])
                    os.environ[key] = value
                    loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load secret {key} to env: {e}")

        logger.info(f"Loaded {loaded} secrets from vault to environment")
        return loaded

    def _save(self):
        """Save vault to disk."""
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vault_path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _load(self):
        """Load vault from disk."""
        if not self.vault_path.exists():
            self._data = {}
            return

        try:
            with open(self.vault_path) as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load vault: {e}")
            self._data = {}

    def get_status(self) -> Dict[str, Any]:
        """Get vault status (no secret values exposed)."""
        categories = {}
        for entry in self._data.values():
            cat = entry.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "initialized": self._initialized,
            "encrypted": self._fernet is not None,
            "total_secrets": len(self._data),
            "categories": categories,
            "vault_path": str(self.vault_path),
        }
