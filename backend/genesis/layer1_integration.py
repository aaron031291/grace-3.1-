"""
Layer 1 Complete Integration: All Input Sources

Layer 1 includes ALL input pathways:
- User inputs (chat, commands, interactions)
- File uploads
- External APIs
- Web scraping / HTML
- Memory mesh
- Learning memory
- Whitelist operations
- System events

Everything flows through Layer 1 → Genesis Key → Version Control → Librarian → Immutable Memory → RAG → World Model
"""
import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, BinaryIO
from pathlib import Path
from sqlalchemy.orm import Session

from genesis.pipeline_integration import get_data_pipeline
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType, GenesisKey
from cognitive.memory_mesh_integration import MemoryMeshIntegration

logger = logging.getLogger(__name__)

# Import trigger pipeline (lazy import to avoid circular dependency)
_genesis_trigger_pipeline = None


def _get_trigger_pipeline():
    """Lazy import to avoid circular dependency."""
    global _genesis_trigger_pipeline
    if _genesis_trigger_pipeline is None:
        from genesis.autonomous_triggers import get_genesis_trigger_pipeline
        _genesis_trigger_pipeline = get_genesis_trigger_pipeline
    return _genesis_trigger_pipeline


class Layer1Integration:
    """
    Complete Layer 1 Integration - ALL input sources flow through here.

    Input Sources:
    1. User inputs (chat, commands, UI interactions)
    2. File uploads (documents, images, code files)
    3. External APIs (REST, GraphQL, webhooks)
    4. Web scraping / HTML (crawled data, parsed content)
    5. Memory mesh (system memory, knowledge graph)
    6. Learning memory (AI learning, model training data)
    7. Whitelist operations (approved sources, trusted data)
    8. System events (errors, logs, telemetry)
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.pipeline = get_data_pipeline(session)
        self.genesis_service = get_genesis_service(session)

        # Layer 1 storage paths
        self.layer1_base = "knowledge_base/layer_1"
        self._ensure_layer1_structure()

        # Layer 1 metadata
        self.metadata_file = os.path.join(self.layer1_base, ".layer1_metadata.json")
        self._load_or_create_metadata()

        # Memory mesh integration
        self.memory_mesh = MemoryMeshIntegration(session, Path("knowledge_base")) if session else None

    def _ensure_layer1_structure(self):
        """Ensure complete Layer 1 directory structure."""
        layer1_paths = [
            "knowledge_base/layer_1",
            "knowledge_base/layer_1/genesis_key",
            "knowledge_base/layer_1/uploads",
            "knowledge_base/layer_1/external_apis",
            "knowledge_base/layer_1/web_scraping",
            "knowledge_base/layer_1/memory_mesh",
            "knowledge_base/layer_1/learning_memory",
            "knowledge_base/layer_1/whitelist"
        ]

        for path in layer1_paths:
            os.makedirs(path, exist_ok=True)

    def _load_or_create_metadata(self):
        """Load or create Layer 1 metadata."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "input_sources": {
                    "user_inputs": 0,
                    "file_uploads": 0,
                    "external_apis": 0,
                    "web_scraping": 0,
                    "memory_mesh": 0,
                    "learning_memory": 0,
                    "whitelist": 0,
                    "system_events": 0
                },
                "total_inputs": 0
            }
            self._save_metadata()

    def _save_metadata(self):
        """Save Layer 1 metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

    # ============================================================
    # 1. USER INPUTS
    # ============================================================

    def process_user_input(
        self,
        user_input: str,
        user_id: str,
        input_type: str = "chat",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process user input through Layer 1.

        Args:
            user_input: User's input text
            user_id: Genesis ID of user
            input_type: Type of input (chat, command, ui_interaction)
            metadata: Additional metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing user input from {user_id}")

        result = self.pipeline.process_input(
            input_data=user_input,
            input_type="user_input",
            user_id=user_id,
            description=f"User {input_type}: {user_input[:50]}..."
        )

        self.metadata["input_sources"]["user_inputs"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        # NEW: Trigger autonomous actions based on Genesis Key
        self._trigger_autonomous_actions(result)

        return result

    # ============================================================
    # 2. FILE UPLOADS
    # ============================================================

    def process_file_upload(
        self,
        file_content: bytes,
        file_name: str,
        file_type: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process file upload through Layer 1.

        Args:
            file_content: Raw file bytes
            file_name: Name of file
            file_type: MIME type or extension
            user_id: Genesis ID of uploader
            metadata: Additional file metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing file upload '{file_name}' from {user_id}")

        # Save file to Layer 1 uploads folder
        upload_path = os.path.join(
            self.layer1_base,
            "uploads",
            user_id,
            datetime.utcnow().strftime("%Y-%m-%d")
        )
        os.makedirs(upload_path, exist_ok=True)

        file_path = os.path.join(upload_path, file_name)
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Compute file hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Process through pipeline
        result = self.pipeline.process_input(
            input_data={
                "file_name": file_name,
                "file_type": file_type,
                "file_size": len(file_content),
                "file_hash": file_hash,
                "file_path": file_path
            },
            input_type="file_upload",
            user_id=user_id,
            file_path=file_path,
            description=f"File upload: {file_name}"
        )

        self.metadata["input_sources"]["file_uploads"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        # NEW: Trigger autonomous actions based on Genesis Key
        self._trigger_autonomous_actions(result)

        return result

    # ============================================================
    # 3. EXTERNAL APIs
    # ============================================================

    def process_external_api(
        self,
        api_name: str,
        api_endpoint: str,
        api_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process external API data through Layer 1.

        Args:
            api_name: Name of API (e.g., "OpenAI", "GitHub")
            api_endpoint: API endpoint called
            api_data: Data received from API
            user_id: Genesis ID if user-initiated
            metadata: Additional API metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing external API '{api_name}' data")

        # Save API data to Layer 1 external_apis folder
        api_path = os.path.join(
            self.layer1_base,
            "external_apis",
            api_name,
            datetime.utcnow().strftime("%Y-%m-%d")
        )
        os.makedirs(api_path, exist_ok=True)

        # Save API response
        timestamp = datetime.utcnow().timestamp()
        api_file = os.path.join(api_path, f"api_response_{timestamp}.json")
        with open(api_file, 'w') as f:
            json.dump(api_data, f, indent=2, default=str)

        # Process through pipeline
        result = self.pipeline.process_input(
            input_data=api_data,
            input_type="external_api",
            user_id=user_id or "system",
            description=f"External API: {api_name} - {api_endpoint}"
        )

        self.metadata["input_sources"]["external_apis"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        return result

    # ============================================================
    # 4. WEB SCRAPING / HTML
    # ============================================================

    def process_web_scraping(
        self,
        url: str,
        html_content: str,
        parsed_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process web scraping data through Layer 1.

        Args:
            url: URL that was scraped
            html_content: Raw HTML content
            parsed_data: Parsed/extracted data
            user_id: Genesis ID if user-initiated
            metadata: Additional scraping metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing web scraping from {url}")

        # Save scraping data to Layer 1 web_scraping folder
        domain = url.split("//")[1].split("/")[0].replace(".", "_")
        scraping_path = os.path.join(
            self.layer1_base,
            "web_scraping",
            domain,
            datetime.utcnow().strftime("%Y-%m-%d")
        )
        os.makedirs(scraping_path, exist_ok=True)

        # Save HTML and parsed data
        timestamp = datetime.utcnow().timestamp()
        html_file = os.path.join(scraping_path, f"scrape_{timestamp}.html")
        data_file = os.path.join(scraping_path, f"parsed_{timestamp}.json")

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        with open(data_file, 'w') as f:
            json.dump(parsed_data, f, indent=2, default=str)

        # Process through pipeline
        result = self.pipeline.process_input(
            input_data=parsed_data,
            input_type="web_scraping",
            user_id=user_id or "system",
            description=f"Web scraping: {url}"
        )

        self.metadata["input_sources"]["web_scraping"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        return result

    # ============================================================
    # 5. MEMORY MESH
    # ============================================================

    def process_memory_mesh(
        self,
        memory_type: str,
        memory_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process memory mesh data through Layer 1.

        Args:
            memory_type: Type of memory (system, knowledge_graph, context)
            memory_data: Memory data
            user_id: Genesis ID if user-specific
            metadata: Additional memory metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing memory mesh ({memory_type})")

        # Save memory to Layer 1 memory_mesh folder
        memory_path = os.path.join(
            self.layer1_base,
            "memory_mesh",
            memory_type,
            datetime.utcnow().strftime("%Y-%m-%d")
        )
        os.makedirs(memory_path, exist_ok=True)

        # Save memory data
        timestamp = datetime.utcnow().timestamp()
        memory_file = os.path.join(memory_path, f"memory_{timestamp}.json")
        with open(memory_file, 'w') as f:
            json.dump(memory_data, f, indent=2, default=str)

        # Process through pipeline
        result = self.pipeline.process_input(
            input_data=memory_data,
            input_type="memory_mesh",
            user_id=user_id or "system",
            description=f"Memory mesh: {memory_type}"
        )

        self.metadata["input_sources"]["memory_mesh"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        return result

    # ============================================================
    # 6. LEARNING MEMORY
    # ============================================================

    def process_learning_memory(
        self,
        learning_type: str,
        learning_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process learning memory through Layer 1.

        This now integrates with the memory mesh system:
        1. Saves to Layer 1 learning_memory folder
        2. Processes through Genesis pipeline
        3. FEEDS INTO MEMORY MESH with trust scoring
        4. High-trust data flows to episodic/procedural memory

        Args:
            learning_type: Type of learning (training, feedback, pattern, success, failure)
            learning_data: Learning data with context, action, outcome
            user_id: Genesis ID if user-specific
            metadata: Additional learning metadata

        Returns:
            Complete pipeline result + memory mesh integration
        """
        logger.info(f"Layer 1: Processing learning memory ({learning_type}) → Memory Mesh")

        # Save learning to Layer 1 learning_memory folder
        learning_path = os.path.join(
            self.layer1_base,
            "learning_memory",
            learning_type,
            datetime.utcnow().strftime("%Y-%m-%d")
        )
        os.makedirs(learning_path, exist_ok=True)

        # Save learning data
        timestamp = datetime.utcnow().timestamp()
        learning_file = os.path.join(learning_path, f"learning_{timestamp}.json")
        with open(learning_file, 'w') as f:
            json.dump(learning_data, f, indent=2, default=str)

        # Process through pipeline (Genesis Key → Version Control → Librarian)
        result = self.pipeline.process_input(
            input_data=learning_data,
            input_type="learning_memory",
            user_id=user_id or "system",
            description=f"Learning memory: {learning_type}"
        )

        # NEW: Feed into memory mesh with trust scoring
        if self.memory_mesh and self.session:
            try:
                # Extract experience components
                context = learning_data.get('context', {})
                action_taken = learning_data.get('action', {})
                outcome = learning_data.get('outcome', {})
                expected_outcome = learning_data.get('expected_outcome')

                # Determine source based on learning type
                if learning_type == 'feedback':
                    source = 'user_feedback_positive' if outcome.get('positive') else 'user_feedback_negative'
                elif learning_type == 'success':
                    source = 'system_observation_success'
                elif learning_type == 'failure':
                    source = 'system_observation_failure'
                elif learning_type == 'correction':
                    source = 'user_feedback_correction'
                else:
                    source = 'system_observation'

                # Ingest into memory mesh
                learning_example_id = self.memory_mesh.ingest_learning_experience(
                    experience_type=learning_type,
                    context=context,
                    action_taken=action_taken,
                    outcome=outcome,
                    expected_outcome=expected_outcome,
                    source=source,
                    user_id=user_id,
                    genesis_key_id=result.get('genesis_key_id')
                )

                # Add memory mesh info to result
                result['memory_mesh'] = {
                    'learning_example_id': learning_example_id,
                    'integrated': True,
                    'message': 'Learning data integrated into memory mesh with trust scoring'
                }

                logger.info(f"Learning memory integrated into memory mesh: {learning_example_id}")

            except Exception as e:
                logger.error(f"Error integrating with memory mesh: {e}")
                result['memory_mesh'] = {
                    'integrated': False,
                    'error': str(e)
                }

        self.metadata["input_sources"]["learning_memory"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        # NEW: Trigger autonomous actions based on Genesis Key
        self._trigger_autonomous_actions(result)

        return result

    # ============================================================
    # 7. WHITELIST
    # ============================================================

    def process_whitelist(
        self,
        whitelist_type: str,
        whitelist_data: Dict,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process whitelist operations through Layer 1.

        Args:
            whitelist_type: Type of whitelist (source, domain, api)
            whitelist_data: Whitelist data
            user_id: Genesis ID of admin
            metadata: Additional whitelist metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing whitelist ({whitelist_type})")

        # Save whitelist to Layer 1 whitelist folder
        whitelist_path = os.path.join(
            self.layer1_base,
            "whitelist",
            whitelist_type
        )
        os.makedirs(whitelist_path, exist_ok=True)

        # Save whitelist data
        timestamp = datetime.utcnow().timestamp()
        whitelist_file = os.path.join(whitelist_path, f"whitelist_{timestamp}.json")
        with open(whitelist_file, 'w') as f:
            json.dump(whitelist_data, f, indent=2, default=str)

        # Process through pipeline
        result = self.pipeline.process_input(
            input_data=whitelist_data,
            input_type="whitelist",
            user_id=user_id or "system",
            description=f"Whitelist: {whitelist_type}"
        )

        self.metadata["input_sources"]["whitelist"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        return result

    # ============================================================
    # 8. SYSTEM EVENTS
    # ============================================================

    def process_system_event(
        self,
        event_type: str,
        event_data: Dict,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process system events through Layer 1.

        Args:
            event_type: Type of event (error, log, telemetry)
            event_data: Event data
            metadata: Additional event metadata

        Returns:
            Complete pipeline result
        """
        logger.info(f"Layer 1: Processing system event ({event_type})")

        # Process through pipeline
        result = self.pipeline.process_input(
            input_data=event_data,
            input_type="system_event",
            user_id="system",
            description=f"System event: {event_type}"
        )

        self.metadata["input_sources"]["system_events"] += 1
        self.metadata["total_inputs"] += 1
        self._save_metadata()

        return result

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def get_layer1_stats(self) -> Dict[str, Any]:
        """Get Layer 1 statistics."""
        return {
            "total_inputs": self.metadata["total_inputs"],
            "input_sources": self.metadata["input_sources"],
            "layer1_paths": {
                "genesis_key": f"{self.layer1_base}/genesis_key",
                "uploads": f"{self.layer1_base}/uploads",
                "external_apis": f"{self.layer1_base}/external_apis",
                "web_scraping": f"{self.layer1_base}/web_scraping",
                "memory_mesh": f"{self.layer1_base}/memory_mesh",
                "learning_memory": f"{self.layer1_base}/learning_memory",
                "whitelist": f"{self.layer1_base}/whitelist"
            },
            "message": "Complete Layer 1 statistics"
        }

    def verify_layer1_structure(self) -> Dict[str, Any]:
        """Verify Layer 1 directory structure is complete."""
        required_paths = [
            "knowledge_base/layer_1",
            "knowledge_base/layer_1/genesis_key",
            "knowledge_base/layer_1/uploads",
            "knowledge_base/layer_1/external_apis",
            "knowledge_base/layer_1/web_scraping",
            "knowledge_base/layer_1/memory_mesh",
            "knowledge_base/layer_1/learning_memory",
            "knowledge_base/layer_1/whitelist"
        ]

        verification = {}
        for path in required_paths:
            verification[path] = os.path.exists(path)

        all_exist = all(verification.values())

        return {
            "layer1_complete": all_exist,
            "paths": verification,
            "message": "Layer 1 structure complete" if all_exist else "Some paths missing"
        }

    # ============================================================
    # AUTONOMOUS TRIGGER INTEGRATION
    # ============================================================

    def _trigger_autonomous_actions(self, pipeline_result: Dict[str, Any]):
        """
        Trigger autonomous actions based on Genesis Key created by pipeline.

        This is the CENTRAL INTEGRATION POINT where Genesis Keys trigger
        autonomous learning, practice, and self-improvement loops.

        Args:
            pipeline_result: Result from data pipeline containing genesis_key_id
        """
        genesis_key_id = pipeline_result.get('genesis_key_id')

        if not genesis_key_id or not self.session:
            return

        try:
            # Get the Genesis Key that was just created
            genesis_key = self.session.query(GenesisKey).filter_by(
                key_id=genesis_key_id
            ).first()

            if not genesis_key:
                logger.warning(f"Genesis Key {genesis_key_id} not found for trigger")
                return

            # Get trigger pipeline
            get_trigger = _get_trigger_pipeline()
            trigger_pipeline = get_trigger(session=self.session, knowledge_base_path=Path(self.layer1_base))

            # TRIGGER AUTONOMOUS ACTIONS
            trigger_result = trigger_pipeline.on_genesis_key_created(genesis_key)

            if trigger_result.get('triggered'):
                actions = trigger_result.get('actions_triggered', [])
                logger.info(
                    f"[LAYER1-TRIGGER] Genesis Key {genesis_key_id} triggered "
                    f"{len(actions)} autonomous actions"
                )

                for action in actions:
                    logger.info(f"  → {action.get('action')}: {action.get('topic', action.get('skill', 'N/A'))}")

        except Exception as e:
            logger.error(f"Error triggering autonomous actions: {e}")
            import traceback
            traceback.print_exc()


# Global Layer 1 integration instance
_layer1_integration: Optional[Layer1Integration] = None


def get_layer1_integration(session: Optional[Session] = None) -> Layer1Integration:
    """Get or create global Layer 1 integration instance."""
    global _layer1_integration
    if _layer1_integration is None or session is not None:
        _layer1_integration = Layer1Integration(session=session)
    return _layer1_integration
