"""
Version Control Connector for Layer 1 Message Bus.

Automatically creates Genesis Keys + Version entries for all file operations.
This connector makes version control AUTONOMOUS - any file change processed
through Layer 1 automatically gets tracked with full version history.

UPDATED: Now fully integrated with Layer 1 message bus with autonomous actions.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations (SCALABILITY)
_executor = ThreadPoolExecutor(max_workers=4)

# Optional import for message bus integration
try:
    from layer1.message_bus import (
        Layer1MessageBus,
        ComponentType,
        Message,
        get_message_bus
    )
    _HAS_MESSAGE_BUS = True
except ImportError:
    _HAS_MESSAGE_BUS = False
    Layer1MessageBus = None
    ComponentType = None
    Message = None


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

    def __init__(self, message_bus: Optional[Layer1MessageBus] = None):
        self.connector_id = "version_control"
        self.enabled = True
        self.operations_tracked = 0
        self.symbiotic_vc = None
        self.message_bus = message_bus

        # Set up Layer 1 integration if available
        if _HAS_MESSAGE_BUS and self.message_bus is None:
            try:
                self.message_bus = get_message_bus()
            except Exception:
                pass

        if self.message_bus:
            self._register_autonomous_actions()
            self._register_request_handlers()
            self._subscribe_to_events()
            logger.info("[VERSION-CONTROL-CONNECTOR] Registered with message bus")
        else:
            logger.info("Version Control Connector initialized (standalone mode)")

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

        # Check if Genesis tracking is disabled
        try:
            from settings import settings
            if settings.DISABLE_GENESIS_TRACKING:
                return {
                    "status": "skipped",
                    "reason": "Genesis tracking disabled (DISABLE_GENESIS_TRACKING=true)",
                    "connector": self.connector_id
                }
        except Exception:
            pass  # If settings unavailable, continue

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

    # ================================================================
    # LAYER 1 MESSAGE BUS INTEGRATION
    # ================================================================

    def _register_autonomous_actions(self):
        """Register autonomous actions for version control."""
        if not self.message_bus or not _HAS_MESSAGE_BUS:
            return

        # 1. Auto-track file when ingestion completes
        self.message_bus.register_autonomous_action(
            trigger_event="ingestion.file_processed",
            action=self._on_file_ingested,
            component=ComponentType.VERSION_CONTROL,
            description="Auto-track file version when ingested"
        )

        # 2. Auto-track when file is uploaded
        self.message_bus.register_autonomous_action(
            trigger_event="ingestion.file_uploaded",
            action=self._on_file_uploaded,
            component=ComponentType.VERSION_CONTROL,
            description="Auto-track file version when uploaded"
        )

        logger.info("[VERSION-CONTROL-CONNECTOR] Registered 2 autonomous actions")

    def _register_request_handlers(self):
        """Register request handlers for version control."""
        if not self.message_bus or not _HAS_MESSAGE_BUS:
            return

        self.message_bus.register_request_handler(
            component=ComponentType.VERSION_CONTROL,
            topic="get_file_history",
            handler=self._handle_get_file_history
        )

        self.message_bus.register_request_handler(
            component=ComponentType.VERSION_CONTROL,
            topic="track_file_change",
            handler=self._handle_track_file_change
        )

        logger.info("[VERSION-CONTROL-CONNECTOR] Registered 2 request handlers")

    def _subscribe_to_events(self):
        """Subscribe to events from other components."""
        if not self.message_bus or not _HAS_MESSAGE_BUS:
            return

        # Subscribe to Genesis Key events to link versions
        self.message_bus.subscribe(
            topic="genesis_keys.new_file_key",
            handler=self._on_genesis_key_created
        )

        logger.info("[VERSION-CONTROL-CONNECTOR] Subscribed to 1 event topic")

    # ================================================================
    # AUTONOMOUS EVENT HANDLERS
    # ================================================================

    async def _on_file_ingested(self, message: Message):
        """Handle file ingestion - auto-track version."""
        file_path = message.payload.get("file_path")
        genesis_key_id = message.payload.get("genesis_key_id")
        chunks_created = message.payload.get("chunks_created", 0)

        logger.info(
            f"[VERSION-CONTROL-CONNECTOR] File ingested: {file_path}"
        )

        # Track the file change
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: self.on_file_ingest(file_path, "system", chunks_created)
        )

        # Publish version tracked event
        if self.message_bus and result.get("status") == "success":
            await self.message_bus.publish(
                topic="version_control.file_tracked",
                payload={
                    "file_path": file_path,
                    "genesis_key": result.get("genesis_key"),
                    "version_number": result.get("version_number"),
                    "operation": "ingest",
                    "timestamp": datetime.utcnow().isoformat()
                },
                from_component=ComponentType.VERSION_CONTROL
            )

    async def _on_file_uploaded(self, message: Message):
        """Handle file upload - auto-track version."""
        file_path = message.payload.get("file_path")
        user_id = message.payload.get("user_id", "system")

        logger.info(
            f"[VERSION-CONTROL-CONNECTOR] File uploaded: {file_path}"
        )

        # Track the file change
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: self.on_file_upload(file_path, user_id)
        )

        # Publish version tracked event
        if self.message_bus and result.get("status") == "success":
            await self.message_bus.publish(
                topic="version_control.file_tracked",
                payload={
                    "file_path": file_path,
                    "genesis_key": result.get("genesis_key"),
                    "version_number": result.get("version_number"),
                    "operation": "upload",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                from_component=ComponentType.VERSION_CONTROL
            )

    async def _on_genesis_key_created(self, message: Message):
        """Handle Genesis Key creation - link to version control."""
        genesis_key_id = message.payload.get("genesis_key_id")
        file_path = message.payload.get("file_path")

        logger.info(
            f"[VERSION-CONTROL-CONNECTOR] Genesis Key created for: {file_path}"
        )

        # Could link version to Genesis Key here
        # For now, just log the connection

    # ================================================================
    # REQUEST HANDLERS
    # ================================================================

    async def _handle_get_file_history(self, message: Message) -> Dict[str, Any]:
        """Handle request for file version history."""
        file_path = message.payload.get("file_path")

        def _get_history():
            try:
                symbiotic = self._get_symbiotic_vc()
                return symbiotic.get_file_history(file_path)
            except Exception as e:
                return {"error": str(e)}

        loop = asyncio.get_event_loop()
        history = await loop.run_in_executor(_executor, _get_history)

        return {
            "file_path": file_path,
            "history": history
        }

    async def _handle_track_file_change(self, message: Message) -> Dict[str, Any]:
        """Handle request to track a file change."""
        file_path = message.payload.get("file_path")
        user_id = message.payload.get("user_id", "system")
        operation = message.payload.get("operation", "modify")
        description = message.payload.get("description", "File changed")

        def _track():
            return self.on_message({
                "input_type": "file",
                "file_path": file_path,
                "user_id": user_id,
                "what_description": description,
                "operation_type": operation
            })

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _track)

        # Publish commit event for Genesis Keys to link
        if self.message_bus and result.get("status") == "success":
            await self.message_bus.publish(
                topic="version_control.commit_created",
                payload={
                    "commit_hash": result.get("genesis_key", "unknown"),
                    "file_path": file_path,
                    "affected_files": [file_path],
                    "user_id": user_id,
                    "description": description,
                    "timestamp": datetime.utcnow().isoformat()
                },
                from_component=ComponentType.VERSION_CONTROL
            )

        return result

    # ================================================================
    # ASYNC VARIANTS (SCALABILITY)
    # ================================================================

    async def on_message_async(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async version of on_message for non-blocking operation.

        Offloads blocking symbiotic VC operations to thread pool.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.on_message, message)

    async def on_file_upload_async(
        self,
        file_path: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Async version of on_file_upload."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.on_file_upload(file_path, user_id, metadata)
        )

    async def on_file_ingest_async(
        self,
        file_path: str,
        user_id: str,
        chunks_created: int = 0
    ) -> Dict[str, Any]:
        """Async version of on_file_ingest."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.on_file_ingest(file_path, user_id, chunks_created)
        )

    async def on_file_modify_async(
        self,
        file_path: str,
        user_id: str,
        reason: str = "File modified"
    ) -> Dict[str, Any]:
        """Async version of on_file_modify."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.on_file_modify(file_path, user_id, reason)
        )

    async def get_statistics_async(self) -> Dict[str, Any]:
        """Async version of get_statistics."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.get_statistics)


# Global connector instance
_version_control_connector: Optional[VersionControlConnector] = None


def get_version_control_connector() -> VersionControlConnector:
    """Get or create the global version control connector instance."""
    global _version_control_connector
    if _version_control_connector is None:
        _version_control_connector = VersionControlConnector()
    return _version_control_connector
