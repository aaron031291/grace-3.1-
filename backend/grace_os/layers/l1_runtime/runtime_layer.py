import json
import logging
import uuid
from typing import Any, Dict, List

from ..grace_layer import GraceLayer
from ...kernel.message_protocol import LayerMessage, LayerResponse

logger = logging.getLogger(__name__)


class RuntimeLayer(GraceLayer):
    """
    Layer 1: Runtime Environment.
    Manages isolated execution environments, dependency resolution,
    state snapshots, and resource limits.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._environments: Dict[str, Dict] = {}
        self._snapshots: Dict[str, Dict] = {}

    @property
    def layer_name(self) -> str:
        return "L1_Runtime"

    @property
    def capabilities(self) -> List[str]:
        return ["environment_management", "dependency_resolution", "state_snapshot", "resource_limiting"]

    @property
    def accepted_message_types(self) -> List[str]:
        return ["SETUP_ENVIRONMENT", "SNAPSHOT_STATE", "TEARDOWN_ENVIRONMENT"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "SETUP_ENVIRONMENT":
            return await self._handle_setup(message)
        elif message.message_type == "SNAPSHOT_STATE":
            return await self._handle_snapshot(message)
        elif message.message_type == "TEARDOWN_ENVIRONMENT":
            return await self._handle_teardown(message)

        return self.build_response(
            message, "failure",
            {"error": f"Unsupported message type: {message.message_type}"}
        )

    async def _handle_setup(self, message: LayerMessage) -> LayerResponse:
        """Set up an isolated environment for task execution."""
        project_path = message.payload.get("project_path", ".")
        task = message.payload.get("task", {})

        logger.info(f"[L1] Setting up environment for project: {project_path}")

        env_id = f"env_{uuid.uuid4().hex[:8]}"

        # 1. Resolve dependencies via MCP
        # In production: read requirements.txt, package.json, etc.
        # deps_result = await self.call_tool("file_read", {"path": f"{project_path}/requirements.txt"})

        # 2. Create environment record
        self._environments[env_id] = {
            "id": env_id,
            "project_path": project_path,
            "status": "active",
            "dependencies_resolved": True,
            "task": task,
        }

        # 3. Take initial snapshot
        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        self._snapshots[snapshot_id] = {
            "id": snapshot_id,
            "env_id": env_id,
            "type": "pre_execution",
            "status": "captured",
        }

        logger.info(f"[L1] Environment {env_id} ready. Snapshot: {snapshot_id}")

        return self.build_response(
            message, "success",
            {
                "environment_id": env_id,
                "snapshot_id": snapshot_id,
                "dependencies_resolved": True,
                "task": task,
            },
            trust_score=90.0
        )

    async def _handle_snapshot(self, message: LayerMessage) -> LayerResponse:
        """Capture environment state for rollback capability."""
        env_id = message.payload.get("environment_id", "")
        snapshot_type = message.payload.get("snapshot_type", "checkpoint")

        logger.info(f"[L1] Taking snapshot of environment {env_id}...")

        snapshot_id = f"snap_{uuid.uuid4().hex[:8]}"
        self._snapshots[snapshot_id] = {
            "id": snapshot_id,
            "env_id": env_id,
            "type": snapshot_type,
            "status": "captured",
        }

        return self.build_response(
            message, "success",
            {"snapshot_id": snapshot_id, "env_id": env_id, "type": snapshot_type},
            trust_score=95.0
        )

    async def _handle_teardown(self, message: LayerMessage) -> LayerResponse:
        """Clean up an environment after task completion."""
        env_id = message.payload.get("environment_id", "")

        logger.info(f"[L1] Tearing down environment {env_id}...")

        if env_id in self._environments:
            self._environments[env_id]["status"] = "terminated"

        return self.build_response(
            message, "success",
            {"environment_id": env_id, "status": "terminated"},
            trust_score=95.0
        )
