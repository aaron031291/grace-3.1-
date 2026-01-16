"""
Version Handshake System
========================
Manages version compatibility between launcher, backend, embeddings, and IDE bridge.

This is a strict system: version mismatches cause immediate failure.
No "it worked yesterday" - versions must match or the system refuses to start.
"""

from typing import Dict, Optional
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class VersionMismatchError(Exception):
    """Raised when version handshake fails."""
    pass


class VersionManager:
    """
    Manages version information and handshakes.
    
    Dumb by design: just reads version files, no business logic.
    """
    
    # Current launcher version - increment ONLY when launcher contract changes
    LAUNCHER_VERSION = "1.0.0"
    
    # Required protocol versions
    REQUIRED_PROTOCOLS = {
        "backend_api": "1.0",
        "embeddings": "1.0",
        "ide_bridge": "1.0"
    }
    
    def __init__(self, version_file: Optional[Path] = None):
        """
        Initialize version manager.
        
        Args:
            version_file: Path to version manifest file (defaults to launcher/versions.json)
        """
        if version_file is None:
            version_file = Path(__file__).parent / "versions.json"
        self.version_file = version_file
        self._versions: Optional[Dict[str, str]] = None
    
    def load_versions(self) -> Dict[str, str]:
        """
        Load version manifest from file.
        
        Returns:
            Dict mapping component names to versions
            
        Raises:
            FileNotFoundError: If version file doesn't exist
            json.JSONDecodeError: If version file is invalid
        """
        if self._versions is not None:
            return self._versions
        
        if not self.version_file.exists():
            raise FileNotFoundError(
                f"Version file not found: {self.version_file}\n"
                f"System cannot verify compatibility without version manifest."
            )
        
        try:
            with open(self.version_file, 'r') as f:
                self._versions = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid version file format: {self.version_file}\n"
                f"Expected valid JSON. Error: {e}",
                e.doc,
                e.pos
            )
        
        return self._versions
    
    def get_backend_version(self) -> str:
        """
        Get backend API version from manifest.
        
        Returns:
            Backend version string
            
        Raises:
            KeyError: If backend version not in manifest
        """
        versions = self.load_versions()
        if "backend" not in versions:
            raise KeyError(
                "Backend version not found in version manifest.\n"
                "Backend must report its version for compatibility check."
            )
        return versions["backend"]
    
    def get_embeddings_version(self) -> str:
        """
        Get embeddings service version from manifest.
        
        Returns:
            Embeddings version string
            
        Raises:
            KeyError: If embeddings version not in manifest
        """
        versions = self.load_versions()
        if "embeddings" not in versions:
            raise KeyError(
                "Embeddings version not found in version manifest.\n"
                "Embeddings must report their version for compatibility check."
            )
        return versions["embeddings"]
    
    def get_ide_bridge_version(self) -> Optional[str]:
        """
        Get IDE bridge version from manifest (optional if not used).
        
        Returns:
            IDE bridge version string, or None if not present
        """
        versions = self.load_versions()
        return versions.get("ide_bridge")
    
    def validate_protocol_compatibility(
        self,
        component: str,
        reported_version: str,
        protocol: str
    ) -> bool:
        """
        Validate that a component's protocol version matches requirements.
        
        Args:
            component: Component name (e.g., "backend", "embeddings")
            reported_version: Version reported by the component
            protocol: Protocol name (e.g., "backend_api", "embeddings")
            
        Returns:
            True if compatible
            
        Raises:
            VersionMismatchError: If versions don't match
        """
        required_version = self.REQUIRED_PROTOCOLS.get(protocol)
        if required_version is None:
            # Protocol not required, skip check
            return True
        
        # Extract protocol version from reported version (e.g., "1.0.0" -> "1.0")
        try:
            reported_protocol = ".".join(reported_version.split(".")[:2])
        except (AttributeError, IndexError):
            raise VersionMismatchError(
                f"Invalid version format from {component}: {reported_version}\n"
                f"Expected semver format (e.g., '1.0.0')."
            )
        
        if reported_protocol != required_version:
            raise VersionMismatchError(
                f"Version mismatch: {component} protocol version {reported_protocol} "
                f"does not match required {required_version}.\n"
                f"Component reported: {reported_version}\n"
                f"Required protocol: {protocol} {required_version}\n"
                f"Update {component} or adjust protocol requirements."
            )
        
        logger.info(f"✓ Version handshake: {component} protocol {protocol} {reported_protocol} ✓")
        return True
    
    def handshake(
        self,
        backend_version: str,
        embeddings_version: Optional[str] = None,
        ide_bridge_version: Optional[str] = None
    ) -> bool:
        """
        Perform full version handshake with all components.
        
        Args:
            backend_version: Version reported by backend
            embeddings_version: Version reported by embeddings service
            ide_bridge_version: Version reported by IDE bridge (optional)
            
        Returns:
            True if all checks pass
            
        Raises:
            VersionMismatchError: If any version mismatch detected
        """
        logger.info("Performing version handshake...")
        
        # Check backend protocol
        self.validate_protocol_compatibility("backend", backend_version, "backend_api")
        
        # Check embeddings protocol (if provided)
        if embeddings_version:
            self.validate_protocol_compatibility("embeddings", embeddings_version, "embeddings")
        
        # Check IDE bridge protocol (if provided)
        if ide_bridge_version:
            self.validate_protocol_compatibility("ide_bridge", ide_bridge_version, "ide_bridge")
        
        logger.info("✓ All version handshakes successful")
        return True
