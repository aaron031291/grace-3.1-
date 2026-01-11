"""
Version Control Connector for Layer 1 Message Bus.

Automatically creates Genesis Keys + Version entries for all file operations.
This connector makes version control AUTONOMOUS - any file change processed
through Layer 1 automatically gets tracked with full version history.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VersionControlConnector:
    """
    Connects Layer 1 inputs to symbiotic version control system.

    When Layer 1 processes file operations, this connector:
    1. Creates Genesis Key for the operation
    2. Creates version entry linked to Genesis Key
    3. Links them bidirectionally
    4. Returns unified result

    This makes version control AUTONOMOUS - no manual calls needed.
    """

    def __init__(self):
        self.connector_id = "version_control"
        self.enabled = True
        self.operations_tracked = 0
        self.symbiotic_vc = None
        logger.info("Version Control Connector initialized")

    def _get_symbiotic_vc(self):
        """Lazy load symbiotic version control to avoid circular imports."""
        if self.symbiotic_vc is None:
            from genesis.symbiotic_version_control import get_symbiotic_version_control
            self.symbiotic_vc = get_symbiotic_version_control()
        return self.symbiotic_vc

    def on_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Layer 1 messages related to file operations.

        Automatically creates Genesis Key + Version entry for:
        - File uploads
        - File modifications
        - File ingestion
        - File processing

        Args:
            message: Layer 1 message containing file operation details

        Returns:
            Result with Genesis Key and version information
        """
        if not self.enabled:
            return {"status": "disabled", "connector": self.connector_id}

        try:
            # Extract file operation details from message
            input_type = message.get("input_type")
            file_path = message.get("file_path") or message.get("where_location")
            user_id = message.get("user_id") or message.get("who_actor", "system")
            description = message.get("what_description", "File operation")
            operation_type = self._determine_operation_type(message)

            # Only track file operations
            if not file_path or input_type not in ["file", "user_file", "file_upload", "ingestion"]:
                return {"status": "skipped", "reason": "Not a file operation"}

            # Track file change symbiotically
            symbiotic = self._get_symbiotic_vc()
            result = symbiotic.track_file_change(
                file_path=file_path,
                user_id=user_id,
                change_description=description,
                operation_type=operation_type
            )

            self.operations_tracked += 1

            logger.info(
                f"Version Control: Tracked {file_path} - "
                f"Genesis Key: {result['operation_genesis_key']}, "
                f"Version: {result.get('version_number', 'N/A')}"
            )

            return {
                "status": "success",
                "connector": self.connector_id,
                "autonomous_action": "version_tracking",
                "genesis_key": result["operation_genesis_key"],
                "version_number": result.get("version_number"),
                "version_key_id": result.get("version_key_id"),
                "file_genesis_key": result["file_genesis_key"],
                "symbiotic": True,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Version Control Connector error: {e}", exc_info=True)
            return {
                "status": "error",
                "connector": self.connector_id,
                "error": str(e)
            }

    def _determine_operation_type(self, message: Dict[str, Any]) -> str:
        """Determine the type of file operation from message."""
        # Check explicit operation type
        if "operation_type" in message:
            return message["operation_type"]

        # Infer from input type
        input_type = message.get("input_type", "")
        if "upload" in input_type.lower():
            return "upload"
        elif "ingest" in input_type.lower():
            return "ingest"
        elif "create" in input_type.lower():
            return "create"
        elif "delete" in input_type.lower():
            return "delete"

        # Check message content
        what = message.get("what_description", "").lower()
        if "upload" in what:
            return "upload"
        elif "create" in what:
            return "create"
        elif "delete" in what:
            return "delete"
        elif "ingest" in what:
            return "ingest"

        # Default to modify
        return "modify"

    def on_file_upload(self, file_path: str, user_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Handle file upload events.

        Args:
            file_path: Path to uploaded file
            user_id: User who uploaded the file
            metadata: Optional metadata about the upload

        Returns:
            Version tracking result
        """
        message = {
            "input_type": "file_upload",
            "file_path": file_path,
            "user_id": user_id,
            "what_description": f"File uploaded: {file_path}",
            "operation_type": "upload"
        }
        if metadata:
            message.update(metadata)

        return self.on_message(message)

    def on_file_ingest(self, file_path: str, user_id: str, chunks_created: int = 0) -> Dict[str, Any]:
        """
        Handle file ingestion events.

        Args:
            file_path: Path to ingested file
            user_id: User who triggered ingestion
            chunks_created: Number of chunks created during ingestion

        Returns:
            Version tracking result
        """
        message = {
            "input_type": "ingestion",
            "file_path": file_path,
            "user_id": user_id,
            "what_description": f"File ingested and processed ({chunks_created} chunks)",
            "operation_type": "ingest",
            "chunks_created": chunks_created
        }

        return self.on_message(message)

    def on_file_modify(self, file_path: str, user_id: str, reason: str = "File modified") -> Dict[str, Any]:
        """
        Handle file modification events.

        Args:
            file_path: Path to modified file
            user_id: User who modified the file
            reason: Reason for modification

        Returns:
            Version tracking result
        """
        message = {
            "input_type": "file",
            "file_path": file_path,
            "user_id": user_id,
            "what_description": reason,
            "operation_type": "modify"
        }

        return self.on_message(message)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about version control connector operations."""
        try:
            symbiotic = self._get_symbiotic_vc()
            symbiotic_stats = symbiotic.get_symbiotic_stats()

            return {
                "connector_id": self.connector_id,
                "enabled": self.enabled,
                "operations_tracked": self.operations_tracked,
                "symbiotic_stats": symbiotic_stats,
                "status": "operational"
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "connector_id": self.connector_id,
                "enabled": self.enabled,
                "operations_tracked": self.operations_tracked,
                "error": str(e)
            }


# Global connector instance
_version_control_connector: Optional[VersionControlConnector] = None


def get_version_control_connector() -> VersionControlConnector:
    """Get or create the global version control connector instance."""
    global _version_control_connector
    if _version_control_connector is None:
        _version_control_connector = VersionControlConnector()
    return _version_control_connector
