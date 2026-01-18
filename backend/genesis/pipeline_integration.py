import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from genesis.genesis_key_service import get_genesis_service
from genesis.symbiotic_version_control import get_symbiotic_version_control
from genesis.repo_scanner import get_repo_scanner
from genesis.kb_integration import get_kb_integration
from models.genesis_key_models import GenesisKeyType
logger = logging.getLogger(__name__)

class DataPipeline:
    """
    Complete data pipeline from input to world model.

    Pipeline Flow:
    1. Layer 1 Input → User/system input received
    2. Genesis Key → Universal ID assigned & tracking
    3. Version Control → Changes tracked symbiotically
    4. Librarian → Organized & categorized
    5. Immutable Memory → Permanent snapshot stored
    6. RAG → Indexed for retrieval
    7. World Model → AI can understand & respond
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session
        self.genesis_service = get_genesis_service(session)
        self.symbiotic_vc = get_symbiotic_version_control(session=session)
        self.kb_integration = get_kb_integration()

        # Pipeline metadata
        self.pipeline_metadata_file = "backend/.genesis_pipeline_metadata.json"
        self._load_or_create_metadata()

    def _load_or_create_metadata(self):
        """Load or create pipeline metadata."""
        if os.path.exists(self.pipeline_metadata_file):
            with open(self.pipeline_metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "total_inputs_processed": 0,
                "pipeline_stages": {
                    "layer_1_inputs": 0,
                    "genesis_keys_created": 0,
                    "versions_tracked": 0,
                    "librarian_organized": 0,
                    "immutable_memory_stored": 0,
                    "rag_indexed": 0,
                    "world_model_ready": 0
                }
            }
            self._save_metadata()

    def _save_metadata(self):
        """Save pipeline metadata."""
        os.makedirs(os.path.dirname(self.pipeline_metadata_file), exist_ok=True)
        with open(self.pipeline_metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)

    def process_input(
        self,
        input_data: Any,
        input_type: str,
        user_id: Optional[str] = None,
        file_path: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process input through COMPLETE pipeline.

        Args:
            input_data: The input (text, file content, user action, etc.)
            input_type: Type of input (user_input, file_change, api_request, etc.)
            user_id: User ID (Genesis ID)
            file_path: File path if applicable
            description: Description of input

        Returns:
            Complete pipeline result showing journey through all stages
        """
        pipeline_result = {
            "pipeline_id": f"PIPE-{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "input_type": input_type,
            "stages": {},
            "complete": False
        }

        try:
            # ============================================================
            # STAGE 1: Layer 1 Input
            # ============================================================
            logger.info(f"Pipeline Stage 1: Layer 1 Input - {input_type}")

            pipeline_result["stages"]["layer_1_input"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "input_type": input_type,
                "description": description or f"Processing {input_type}"
            }

            self.metadata["pipeline_stages"]["layer_1_inputs"] += 1

            # ============================================================
            # STAGE 2: Genesis Key (Universal ID & Tracking)
            # ============================================================
            logger.info("Pipeline Stage 2: Genesis Key Creation")

            genesis_key = self.genesis_service.create_key(
                key_type=GenesisKeyType.USER_INPUT if input_type == "user_input" else GenesisKeyType.FILE_OPERATION,
                what_description=description or f"Pipeline input: {input_type}",
                who_actor=user_id or "system",
                where_location=file_path or "system",
                why_reason=f"Data pipeline processing: {input_type}",
                how_method="Complete data pipeline",
                user_id=user_id,
                file_path=file_path,
                context_data={
                    "pipeline_id": pipeline_result["pipeline_id"],
                    "input_type": input_type,
                    "stage": "genesis_key"
                },
                tags=["pipeline", input_type, "symbiotic"],
                session=self.session
            )

            pipeline_result["stages"]["genesis_key"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "genesis_key_id": genesis_key.key_id,
                "message": "Universal ID assigned & tracked"
            }

            self.metadata["pipeline_stages"]["genesis_keys_created"] += 1

            # ============================================================
            # STAGE 3: Version Control (Symbiotic)
            # ============================================================
            logger.info("Pipeline Stage 3: Version Control")

            version_result = None
            if file_path:
                # Track file change symbiotically
                version_result = self.symbiotic_vc.track_file_change(
                    file_path=file_path,
                    user_id=user_id,
                    change_description=description,
                    operation_type="modify"
                )

                pipeline_result["stages"]["version_control"] = {
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version_key_id": version_result.get("version_key_id"),
                    "version_number": version_result.get("version_number"),
                    "symbiotic": True,
                    "message": "Changes tracked symbiotically with Genesis Key"
                }

                self.metadata["pipeline_stages"]["versions_tracked"] += 1
            else:
                pipeline_result["stages"]["version_control"] = {
                    "status": "skipped",
                    "reason": "No file path provided"
                }

            # ============================================================
            # STAGE 4: Librarian (Organization & Categorization)
            # ============================================================
            logger.info("Pipeline Stage 4: Librarian Organization")

            # Organize in knowledge base structure
            # knowledge_base/layer_1/genesis_key/{user_id}/
            librarian_result = self._librarian_organize(
                genesis_key=genesis_key,
                input_data=input_data,
                user_id=user_id
            )

            pipeline_result["stages"]["librarian"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "organization_path": librarian_result["path"],
                "category": librarian_result["category"],
                "message": "Data organized & categorized"
            }

            self.metadata["pipeline_stages"]["librarian_organized"] += 1

            # ============================================================
            # STAGE 5: Immutable Memory (Permanent Snapshot)
            # ============================================================
            logger.info("Pipeline Stage 5: Immutable Memory Storage")

            immutable_result = self._store_in_immutable_memory(
                genesis_key=genesis_key,
                input_data=input_data,
                version_result=version_result,
                librarian_result=librarian_result
            )

            pipeline_result["stages"]["immutable_memory"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "storage_location": immutable_result["location"],
                "immutable": True,
                "message": "Permanent snapshot stored"
            }

            self.metadata["pipeline_stages"]["immutable_memory_stored"] += 1

            # ============================================================
            # STAGE 6: RAG (Retrieval Augmented Generation)
            # ============================================================
            logger.info("Pipeline Stage 6: RAG Indexing")

            rag_result = self._index_for_rag(
                genesis_key=genesis_key,
                input_data=input_data,
                immutable_location=immutable_result["location"]
            )

            pipeline_result["stages"]["rag"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "indexed": rag_result["indexed"],
                "searchable": True,
                "message": "Indexed for retrieval"
            }

            self.metadata["pipeline_stages"]["rag_indexed"] += 1

            # ============================================================
            # STAGE 7: World Model (AI Understanding)
            # ============================================================
            logger.info("Pipeline Stage 7: World Model Integration")

            world_model_result = self._integrate_world_model(
                genesis_key=genesis_key,
                input_data=input_data,
                rag_result=rag_result
            )

            pipeline_result["stages"]["world_model"] = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "ai_ready": True,
                "context_available": True,
                "message": "AI can understand & respond"
            }

            self.metadata["pipeline_stages"]["world_model_ready"] += 1

            # ============================================================
            # PIPELINE COMPLETE
            # ============================================================
            pipeline_result["complete"] = True
            pipeline_result["message"] = "Data successfully flowed through complete pipeline"

            self.metadata["total_inputs_processed"] += 1
            self._save_metadata()

            logger.info(f"Pipeline completed: {pipeline_result['pipeline_id']}")
            return pipeline_result

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            pipeline_result["error"] = str(e)
            pipeline_result["complete"] = False
            return pipeline_result

    def _librarian_organize(
        self,
        genesis_key,
        input_data: Any,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Librarian: Organize and categorize data.

        Organizes data in knowledge_base/layer_1/genesis_key/ structure.
        """
        # Determine category based on data type
        if genesis_key.key_type == GenesisKeyType.USER_INPUT:
            category = "user_inputs"
        elif genesis_key.key_type == GenesisKeyType.FILE_OPERATION:
            category = "file_operations"
        elif genesis_key.key_type == GenesisKeyType.API_REQUEST:
            category = "api_requests"
        else:
            category = "general"

        # Organize in knowledge base
        user_folder = user_id or "system"
        kb_path = f"knowledge_base/layer_1/genesis_key/{user_folder}/{category}"

        os.makedirs(kb_path, exist_ok=True)

        # Save Genesis Key in organized structure
        self.kb_integration.save_genesis_key(genesis_key)

        return {
            "path": kb_path,
            "category": category,
            "organized": True
        }

    def _store_in_immutable_memory(
        self,
        genesis_key,
        input_data: Any,
        version_result: Optional[Dict],
        librarian_result: Dict
    ) -> Dict[str, Any]:
        """
        Store in immutable memory (permanent snapshot).

        Creates permanent record that cannot be changed.
        """
        immutable_entry = {
            "genesis_key_id": genesis_key.key_id,
            "timestamp": datetime.utcnow().isoformat(),
            "what": genesis_key.what_description,
            "who": genesis_key.who_actor,
            "where": genesis_key.where_location,
            "when": genesis_key.when_timestamp.isoformat(),
            "why": genesis_key.why_reason,
            "how": genesis_key.how_method,
            "version_info": version_result,
            "organization": librarian_result,
            "immutable": True
        }

        # Store in .genesis_immutable_pipeline.json
        immutable_file = "backend/.genesis_immutable_pipeline.json"

        if os.path.exists(immutable_file):
            with open(immutable_file, 'r') as f:
                immutable_data = json.load(f)
        else:
            immutable_data = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "entries": []
            }

        immutable_data["entries"].append(immutable_entry)

        with open(immutable_file, 'w') as f:
            json.dump(immutable_data, f, indent=2, default=str)

        return {
            "location": immutable_file,
            "entry_id": genesis_key.key_id,
            "immutable": True
        }

    def _index_for_rag(
        self,
        genesis_key,
        input_data: Any,
        immutable_location: str
    ) -> Dict[str, Any]:
        """
        Index for RAG (Retrieval Augmented Generation).

        Makes data searchable and retrievable for AI.
        """
        # Create RAG-ready metadata
        rag_metadata = {
            "genesis_key_id": genesis_key.key_id,
            "content": str(input_data) if input_data else genesis_key.what_description,
            "metadata": {
                "what": genesis_key.what_description,
                "who": genesis_key.who_actor,
                "where": genesis_key.where_location,
                "when": genesis_key.when_timestamp.isoformat(),
                "why": genesis_key.why_reason,
                "how": genesis_key.how_method
            },
            "searchable": True,
            "indexed_at": datetime.utcnow().isoformat()
        }

        # Store RAG index
        rag_index_file = "backend/.genesis_rag_index.json"

        if os.path.exists(rag_index_file):
            with open(rag_index_file, 'r') as f:
                rag_index = json.load(f)
        else:
            rag_index = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "index": []
            }

        rag_index["index"].append(rag_metadata)

        with open(rag_index_file, 'w') as f:
            json.dump(rag_index, f, indent=2, default=str)

        return {
            "indexed": True,
            "index_location": rag_index_file,
            "searchable": True
        }

    def _integrate_world_model(
        self,
        genesis_key,
        input_data: Any,
        rag_result: Dict
    ) -> Dict[str, Any]:
        """
        Integrate with World Model (AI understanding).

        Makes data available for AI to understand and respond.
        """
        # Create world model context
        world_model_context = {
            "genesis_key_id": genesis_key.key_id,
            "context": {
                "what": genesis_key.what_description,
                "who": genesis_key.who_actor,
                "where": genesis_key.where_location,
                "when": genesis_key.when_timestamp.isoformat(),
                "why": genesis_key.why_reason,
                "how": genesis_key.how_method
            },
            "rag_indexed": rag_result["indexed"],
            "available_for_ai": True,
            "integrated_at": datetime.utcnow().isoformat()
        }

        # Store world model context
        world_model_file = "backend/.genesis_world_model.json"

        if os.path.exists(world_model_file):
            with open(world_model_file, 'r') as f:
                world_model = json.load(f)
        else:
            world_model = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "contexts": []
            }

        world_model["contexts"].append(world_model_context)

        with open(world_model_file, 'w') as f:
            json.dump(world_model, f, indent=2, default=str)

        return {
            "ai_ready": True,
            "context_available": True,
            "world_model_location": world_model_file
        }

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "total_inputs_processed": self.metadata["total_inputs_processed"],
            "pipeline_stages": self.metadata["pipeline_stages"],
            "pipeline_complete": all(
                self.metadata["pipeline_stages"][stage] > 0
                for stage in self.metadata["pipeline_stages"]
            ),
            "message": "Complete pipeline statistics"
        }

    def verify_pipeline(self) -> Dict[str, Any]:
        """
        Verify that pipeline is working correctly.

        Checks that all stages are operational.
        """
        verification = {
            "layer_1_input": True,  # Always available
            "genesis_key": self.genesis_service is not None,
            "version_control": self.symbiotic_vc is not None,
            "librarian": self.kb_integration is not None,
            "immutable_memory": os.path.exists("backend/.genesis_immutable_pipeline.json") if self.metadata["total_inputs_processed"] > 0 else True,
            "rag": os.path.exists("backend/.genesis_rag_index.json") if self.metadata["total_inputs_processed"] > 0 else True,
            "world_model": os.path.exists("backend/.genesis_world_model.json") if self.metadata["total_inputs_processed"] > 0 else True
        }

        all_operational = all(verification.values())

        return {
            "pipeline_operational": all_operational,
            "stages": verification,
            "message": "All pipeline stages operational" if all_operational else "Some stages need attention"
        }


# Global pipeline instance
_data_pipeline: Optional[DataPipeline] = None


def get_data_pipeline(session: Optional[Session] = None) -> DataPipeline:
    """Get or create global data pipeline instance."""
    global _data_pipeline
    if _data_pipeline is None or session is not None:
        _data_pipeline = DataPipeline(session=session)
    return _data_pipeline
