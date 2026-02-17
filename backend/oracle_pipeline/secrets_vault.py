"""
Secrets Vault - Secure API Key Management

Manages API keys and secrets for all external services.
Keys are loaded from environment variables (.env file),
NEVER stored in code or committed to git.

Supported keys:
- KIMI_API_KEY: Kimi 2.5 reasoning model
- SERPAPI_KEY: SerpAPI for web search
- GITHUB_TOKEN: GitHub API access
- OLLAMA_HOST: Ollama LLM server
- QDRANT_API_KEY: Qdrant vector DB

Usage:
    from oracle_pipeline.secrets_vault import get_vault
    vault = get_vault()
    kimi_key = vault.get_key("KIMI_API_KEY")
"""

import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretsVault:
    """
    Secure secrets management.

    Loads keys from environment variables. The .env file is
    gitignored so keys never enter version control.
    """

    SUPPORTED_KEYS = [
        "KIMI_API_KEY",
        "SERPAPI_KEY",
        "GITHUB_TOKEN",
        "OLLAMA_HOST",
        "QDRANT_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DATABASE_URL",
    ]

    def __init__(self):
        self._loaded = False
        self._load_env()

    def _load_env(self) -> None:
        """Load .env file if it exists."""
        env_paths = [
            Path.cwd() / ".env",
            Path.cwd().parent / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
        ]

        for env_path in env_paths:
            if env_path.exists():
                try:
                    with open(env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, _, value = line.partition("=")
                                key = key.strip()
                                value = value.strip().strip("'\"")
                                if key and value:
                                    os.environ.setdefault(key, value)
                    self._loaded = True
                    logger.info(f"[VAULT] Loaded secrets from {env_path}")
                    return
                except Exception as e:
                    logger.warning(f"[VAULT] Failed to load {env_path}: {e}")

        logger.info("[VAULT] No .env file found, using environment variables only")

    def get_key(self, key_name: str) -> Optional[str]:
        """
        Get a secret key by name.

        Args:
            key_name: Name of the key (e.g., "KIMI_API_KEY")

        Returns:
            Key value or None if not set
        """
        value = os.environ.get(key_name)
        if value:
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            logger.debug(f"[VAULT] Retrieved {key_name}: {masked}")
        return value

    def get_kimi_key(self) -> Optional[str]:
        """Get Kimi API key."""
        return self.get_key("KIMI_API_KEY")

    def get_serpapi_key(self) -> Optional[str]:
        """Get SerpAPI key."""
        return self.get_key("SERPAPI_KEY")

    def get_github_token(self) -> Optional[str]:
        """Get GitHub token."""
        return self.get_key("GITHUB_TOKEN")

    def has_key(self, key_name: str) -> bool:
        """Check if a key is available."""
        return os.environ.get(key_name) is not None

    def get_available_keys(self) -> List[str]:
        """Get list of available (set) keys."""
        return [k for k in self.SUPPORTED_KEYS if self.has_key(k)]

    def get_missing_keys(self) -> List[str]:
        """Get list of missing (unset) keys."""
        return [k for k in self.SUPPORTED_KEYS if not self.has_key(k)]

    def get_status(self) -> Dict[str, bool]:
        """Get status of all supported keys."""
        return {k: self.has_key(k) for k in self.SUPPORTED_KEYS}


_vault: Optional[SecretsVault] = None


def get_vault() -> SecretsVault:
    """Get the global secrets vault instance."""
    global _vault
    if _vault is None:
        _vault = SecretsVault()
    return _vault
