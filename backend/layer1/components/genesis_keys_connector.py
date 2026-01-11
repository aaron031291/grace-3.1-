"""
Genesis Keys Connector - Universal Tracking Integration

Connects Genesis Keys system to Layer 1 message bus for:
- Automatic key creation on ingestion
- User contribution tracking
- Cross-component provenance
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor

from layer1.message_bus import (
    Layer1MessageBus,
    ComponentType,
    Message,
    get_message_bus
)

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations (SCALABILITY)
_executor = ThreadPoolExecutor(max_workers=4)


class GenesisKeysConnector:
    """
    Connects Genesis Keys to Layer 1 message bus.

    Autonomous Actions:
    1. File ingested → Auto-create Genesis Key
    2. Learning created → Auto-create learning Genesis Key
    3. User contribution → Track in user's Genesis profile
    4. Version control commit → Link to Genesis Keys
    """

    def __init__(
        self,
        session,
        kb_path: str,
        message_bus: Optional[Layer1MessageBus] = None
    ):
        self.session = session
        self.kb_path = kb_path
        self.message_bus = message_bus or get_message_bus()

        # Register component
        self.message_bus.register_component(
            ComponentType.GENESIS_KEYS,
            self
        )

        logger.info("[GENESIS-KEYS-CONNECTOR] Registered with message bus")

        # Set up autonomous actions
        self._register_autonomous_actions()
        self._register_request_handlers()
        self._subscribe_to_events()

    # ================================================================
    # AUTONOMOUS ACTIONS
    # ================================================================

    def _register_autonomous_actions(self):
        """Register all autonomous actions for Genesis Keys."""

        # 1. Auto-create Genesis Key on file ingestion
        self.message_bus.register_autonomous_action(
            trigger_event="ingestion.file_processed",
            action=self._on_file_ingested,
            component=ComponentType.GENESIS_KEYS,
            description="Auto-create Genesis Key for ingested file"
        )

        # 2. Auto-create learning Genesis Key
        self.message_bus.register_autonomous_action(
            trigger_event="memory_mesh.learning_created",
            action=self._on_learning_created,
            component=ComponentType.GENESIS_KEYS,
            description="Auto-create Genesis Key for learning experience"
        )

        # 3. Track user contributions
        self.message_bus.register_autonomous_action(
            trigger_event="genesis_keys.new_user_contribution",
            action=self._on_user_contribution,
            component=ComponentType.GENESIS_KEYS,
            description="Track user contribution in Genesis profile"
        )

        logger.info("[GENESIS-KEYS-CONNECTOR] ⭐ Registered 3 autonomous actions")

    # ================================================================
    # EVENT HANDLERS (Autonomous)
    # ================================================================

    async def _on_file_ingested(self, message: Message):
        """Handle file ingestion - auto-create Genesis Key."""
        file_path = message.payload.get("file_path")
        file_type = message.payload.get("file_type")
        document_id = message.payload.get("document_id")

        # Create Genesis Key
        genesis_key_id = self._create_genesis_key(
            key_type="ingestion",
            entity_type=file_type,
            entity_id=document_id,
            metadata={
                "file_path": file_path,
                "file_type": file_type,
                "document_id": document_id
            }
        )

        logger.info(
            f"[GENESIS-KEYS-CONNECTOR] 🤖 Created Genesis Key: {genesis_key_id} "
            f"for file: {file_path}"
        )

        # Publish event
        await self.message_bus.publish(
            topic="genesis_keys.new_file_key",
            payload={
                "genesis_key_id": genesis_key_id,
                "file_path": file_path,
                "document_id": document_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            from_component=ComponentType.GENESIS_KEYS
        )

    async def _on_learning_created(self, message: Message):
        """Handle learning creation - auto-create Genesis Key."""
        learning_id = message.payload.get("learning_id")
        experience_type = message.payload.get("experience_type")
        user_id = message.payload.get("user_id")
        genesis_key_id = message.payload.get("genesis_key_id")

        # If Genesis Key already exists, just link it
        if genesis_key_id:
            logger.info(
                f"[GENESIS-KEYS-CONNECTOR] ✓ Existing Genesis Key: {genesis_key_id}"
            )
            return

        # Create new Genesis Key for learning
        genesis_key_id = self._create_genesis_key(
            key_type="learning",
            entity_type=experience_type,
            entity_id=learning_id,
            metadata={
                "learning_id": learning_id,
                "experience_type": experience_type,
                "user_id": user_id
            }
        )

        logger.info(
            f"[GENESIS-KEYS-CONNECTOR] 🤖 Created Genesis Key: {genesis_key_id} "
            f"for learning: {learning_id}"
        )

        # Publish event
        await self.message_bus.publish(
            topic="genesis_keys.new_learning_key",
            payload={
                "genesis_key_id": genesis_key_id,
                "learning_id": learning_id,
                "learning_type": experience_type,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            from_component=ComponentType.GENESIS_KEYS
        )

    async def _on_user_contribution(self, message: Message):
        """Handle user contribution - track in Genesis profile."""
        user_id = message.payload.get("user_id")
        contribution_type = message.payload.get("contribution_type")
        genesis_key_id = message.payload.get("genesis_key_id")

        logger.info(
            f"[GENESIS-KEYS-CONNECTOR] 🤖 User contribution: {user_id} "
            f"({contribution_type}) → {genesis_key_id}"
        )

        # Track in user profile (simplified for now)
        # In full implementation, would update user's contribution history

        # Publish event
        await self.message_bus.publish(
            topic="genesis_keys.contribution_tracked",
            payload={
                "user_id": user_id,
                "contribution_type": contribution_type,
                "genesis_key_id": genesis_key_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            from_component=ComponentType.GENESIS_KEYS
        )

    # ================================================================
    # REQUEST HANDLERS
    # ================================================================

    def _register_request_handlers(self):
        """Register request handlers for other components."""

        self.message_bus.register_request_handler(
            component=ComponentType.GENESIS_KEYS,
            topic="get_genesis_key",
            handler=self._handle_get_genesis_key
        )

        self.message_bus.register_request_handler(
            component=ComponentType.GENESIS_KEYS,
            topic="get_user_contributions",
            handler=self._handle_get_user_contributions
        )

        self.message_bus.register_request_handler(
            component=ComponentType.GENESIS_KEYS,
            topic="create_file_key",
            handler=self._handle_create_file_key
        )

        logger.info("[GENESIS-KEYS-CONNECTOR] 🔧 Registered 3 request handlers")

    async def _handle_create_file_key(self, message: Message) -> Dict[str, Any]:
        """Handle request to create Genesis Key for a file."""
        file_path = message.payload.get("file_path")
        file_type = message.payload.get("file_type")
        user_id = message.payload.get("user_id")

        def _create_key():
            return self._create_genesis_key(
                key_type="ingestion",
                entity_type=file_type or "file",
                entity_id=file_path,
                metadata={
                    "file_path": file_path,
                    "file_type": file_type,
                    "user_id": user_id,
                    "created_via": "create_file_key_request"
                }
            )

        # Run database operation asynchronously (SCALABILITY)
        loop = asyncio.get_event_loop()
        genesis_key_id = await loop.run_in_executor(_executor, _create_key)

        logger.info(
            f"[GENESIS-KEYS-CONNECTOR] ✓ Created file Genesis Key: {genesis_key_id}"
        )

        return {
            "genesis_key_id": genesis_key_id,
            "file_path": file_path,
            "created": True
        }

    async def _handle_get_genesis_key(self, message: Message) -> Dict[str, Any]:
        """Handle request for Genesis Key details."""
        genesis_key_id = message.payload.get("genesis_key_id")

        def _get_key():
            # Get Genesis Key from database
            from backend.models.database_models import GenesisKey
            genesis_key = self.session.query(GenesisKey).filter(
                GenesisKey.genesis_key_id == genesis_key_id
            ).first()
            return genesis_key

        # Run database query asynchronously (SCALABILITY)
        loop = asyncio.get_event_loop()
        genesis_key = await loop.run_in_executor(_executor, _get_key)

        if not genesis_key:
            return {"error": f"Genesis Key not found: {genesis_key_id}"}

        return {
            "genesis_key_id": genesis_key.genesis_key_id,
            "key_type": genesis_key.key_type,
            "created_at": genesis_key.created_at.isoformat() if genesis_key.created_at else None,
            "immutable": True
        }

    async def _handle_get_user_contributions(self, message: Message) -> Dict[str, Any]:
        """Handle request for user's Genesis Key contributions."""
        user_id = message.payload.get("user_id")

        def _get_contributions():
            # Get user's Genesis Keys
            from backend.models.database_models import GenesisKey
            keys = self.session.query(GenesisKey).filter(
                GenesisKey.metadata.contains(f'"user_id": "{user_id}"')
            ).all()
            return keys

        # Run database query asynchronously (SCALABILITY)
        loop = asyncio.get_event_loop()
        keys = await loop.run_in_executor(_executor, _get_contributions)

        return {
            "user_id": user_id,
            "total_contributions": len(keys),
            "genesis_keys": [
                {
                    "genesis_key_id": key.genesis_key_id,
                    "key_type": key.key_type,
                    "created_at": key.created_at.isoformat() if key.created_at else None
                }
                for key in keys
            ]
        }

    # ================================================================
    # SUBSCRIPTIONS
    # ================================================================

    def _subscribe_to_events(self):
        """Subscribe to events from other components."""

        # Listen for version control commits
        self.message_bus.subscribe(
            topic="version_control.commit_created",
            handler=self._on_commit_created
        )

        logger.info("[GENESIS-KEYS-CONNECTOR] 📡 Subscribed to 1 event topic")

    async def _on_commit_created(self, message: Message):
        """Handle version control commit - link Genesis Keys."""
        commit_hash = message.payload.get("commit_hash")
        affected_files = message.payload.get("affected_files", [])

        logger.info(
            f"[GENESIS-KEYS-CONNECTOR] 📦 Commit created: {commit_hash} "
            f"({len(affected_files)} files)"
        )

        # Could link commit to Genesis Keys of affected files
        # For now, just log

    # ================================================================
    # UTILITIES
    # ================================================================

    def _create_genesis_key(
        self,
        key_type: str,
        entity_type: str,
        entity_id: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Create a new Genesis Key."""
        timestamp = int(datetime.utcnow().timestamp())
        hash_input = f"{key_type}-{entity_type}-{entity_id}-{timestamp}"
        key_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

        genesis_key_id = f"GK-{key_type}-{entity_type}-{timestamp}-{key_hash}"

        # Save to database
        from backend.models.database_models import GenesisKey
        genesis_key = GenesisKey(
            genesis_key_id=genesis_key_id,
            key_type=key_type,
            created_at=datetime.utcnow(),
            immutable=True,
            metadata=metadata
        )

        self.session.add(genesis_key)
        self.session.commit()

        return genesis_key_id


def create_genesis_keys_connector(
    session,
    kb_path: str,
    message_bus: Optional[Layer1MessageBus] = None
) -> GenesisKeysConnector:
    """Create and initialize Genesis Keys connector."""
    connector = GenesisKeysConnector(session, kb_path, message_bus)
    logger.info("[GENESIS-KEYS-CONNECTOR] ✓ Initialized and connected to message bus")
    return connector
