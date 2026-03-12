"""
Genesis Key Generator
Mints immutable cryptographic-style keys to trace component origin
and action provenance across the Grace system.
"""

import uuid
import time
import hashlib

class GenesisKeyGenerator:
    def mint(self, component: str) -> str:
        """
        Produce a traceable Genesis Key mapping to a specific component initialization.
        """
        raw_seed = f"{component}_{time.time()}_{uuid.uuid4().hex}"
        key_hash = hashlib.sha256(raw_seed.encode()).hexdigest()[:12]
        return f"genesis_{component}_{key_hash}"

# Singleton instance
genesis_key = GenesisKeyGenerator()
