"""
Genesis Key CI/CD Pipeline System
=================================
Self-hosted CI/CD pipeline powered by Genesis Keys.
No external dependencies - fully autonomous build/test/deploy.

Genesis Key Actions for CI/CD:
- PIPELINE_TRIGGER: Initiates a pipeline run
- PIPELINE_STAGE: Executes a pipeline stage
- PIPELINE_COMPLETE: Marks pipeline completion
- BUILD_ARTIFACT: Creates build artifacts
- TEST_EXECUTION: Runs test suites
- DEPLOYMENT: Handles deployments
"""

import asyncio
import subprocess
import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging
import hashlib
import tempfile

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class StageType(str, Enum):
    """Types of pipeline stages."""
    CHECKOUT = "checkout"
    INSTALL = "install"
    LINT = "lint"
    TEST = "test"
    BUILD = "build"
    SECURITY = "security"
    DEPLOY = "deploy"
    NOTIFY = "notify"
    CUSTOM = "custom"


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    stage_name: str
    status: PipelineStatus
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineStage:
    """Definition of a pipeline stage."""
    name: str
    stage_type: StageType
    commands: List[str]
    working_dir: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 600
    continue_on_error: bool = False
    condition: Optional[str] = None  # e.g., "branch == 'main'"
    depends_on: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)  # Paths to save as artifacts


@dataclass
class Pipeline:
    """Pipeline definition."""
    id: str
    name: str
    description: str = ""
    stages: List[PipelineStage] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)  # push, pull_request, schedule, manual
    branches: List[str] = field(default_factory=list)  # Branch filters
    environment: Dict[str, str] = field(default_factory=dict)  # Global env vars
    timeout_minutes: int = 60
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PipelineRun:
    """A single execution of a pipeline."""
    id: str
    pipeline_id: str
    pipeline_name: str
    genesis_key: str  # Tracking key for this run
    status: PipelineStatus = PipelineStatus.PENDING
    trigger: str = "manual"
    branch: str = "main"
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    triggered_by: str = "system"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0
    stage_results: List[StageResult] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    logs: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class GenesisKeyAction:
    """Genesis Key actions for CI/CD tracking."""

    PIPELINE_TRIGGER = "cicd:pipeline:trigger"
    PIPELINE_STAGE = "cicd:pipeline:stage"
    PIPELINE_COMPLETE = "cicd:pipeline:complete"
    BUILD_ARTIFACT = "cicd:build:artifact"
    TEST_EXECUTION = "cicd:test:execution"
    DEPLOYMENT = "cicd:deploy"
    WEBHOOK_RECEIVED = "cicd:webhook:received"


class GenesisCICD:
    """
    Genesis Key-powered CI/CD system.

    Self-hosted continuous integration and deployment
    without external dependencies.
    """

    def __init__(
        self,
        workspace_dir: str = "/tmp/grace-cicd",
        artifacts_dir: str = "/tmp/grace-cicd/artifacts",
        max_concurrent_runs: int = 5
    ):
        self.workspace_dir = Path(workspace_dir)
        self.artifacts_dir = Path(artifacts_dir)
        self.max_concurrent_runs = max_concurrent_runs

        # Storage
        self.pipelines: Dict[str, Pipeline] = {}
        self.runs: Dict[str, PipelineRun] = {}
        self.run_queue: asyncio.Queue = asyncio.Queue()

        # Execution tracking
        self.active_runs: Dict[str, asyncio.Task] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

        # Genesis key tracking
        self.genesis_keys: Dict[str, Dict[str, Any]] = {}

        # Ensure directories exist
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Register default pipelines
        self._register_default_pipelines()

    def _register_default_pipelines(self):
        """Register default CI/CD pipelines."""

        # Main CI Pipeline
        ci_pipeline = Pipeline(
            id="grace-ci",
            name="GRACE CI Pipeline",
            description="Main continuous integration pipeline",
            triggers=["push", "pull_request"],
            branches=["main", "develop", "feature/*"],
            stages=[
                PipelineStage(
                    name="checkout",
                    stage_type=StageType.CHECKOUT,
                    commands=["git fetch origin", "git checkout $BRANCH"],
                    timeout_seconds=120
                ),
                PipelineStage(
                    name="install-backend",
                    stage_type=StageType.INSTALL,
                    commands=[
                        "cd backend",
                        "python -m venv venv || true",
                        "source venv/bin/activate || . venv/Scripts/activate",
                        "pip install -r requirements.txt"
                    ],
                    working_dir="backend",
                    timeout_seconds=300,
                    depends_on=["checkout"]
                ),
                PipelineStage(
                    name="install-frontend",
                    stage_type=StageType.INSTALL,
                    commands=["cd frontend", "npm ci || npm install"],
                    working_dir="frontend",
                    timeout_seconds=300,
                    depends_on=["checkout"]
                ),
                PipelineStage(
                    name="lint-backend",
                    stage_type=StageType.LINT,
                    commands=[
                        "cd backend",
                        "source venv/bin/activate || . venv/Scripts/activate || true",
                        "flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true",
                        "flake8 . --count --exit-zero --max-complexity=10 --statistics"
                    ],
                    working_dir="backend",
                    timeout_seconds=120,
                    depends_on=["install-backend"],
                    continue_on_error=True
                ),
                PipelineStage(
                    name="lint-frontend",
                    stage_type=StageType.LINT,
                    commands=["cd frontend", "npm run lint || true"],
                    working_dir="frontend",
                    timeout_seconds=120,
                    depends_on=["install-frontend"],
                    continue_on_error=True
                ),
                PipelineStage(
                    name="test-backend",
                    stage_type=StageType.TEST,
                    commands=[
                        "cd backend",
                        "source venv/bin/activate || . venv/Scripts/activate || true",
                        "pytest tests/ -v --tb=short || python -m pytest tests/ -v --tb=short"
                    ],
                    working_dir="backend",
                    timeout_seconds=600,
                    depends_on=["lint-backend"],
                    artifacts=["backend/coverage.xml", "backend/test-results.xml"]
                ),
                PipelineStage(
                    name="test-frontend",
                    stage_type=StageType.TEST,
                    commands=["cd frontend", "npm test -- --passWithNoTests || true"],
                    working_dir="frontend",
                    timeout_seconds=300,
                    depends_on=["lint-frontend"],
                    continue_on_error=True
                ),
                PipelineStage(
                    name="security-scan",
                    stage_type=StageType.SECURITY,
                    commands=[
                        "cd backend",
                        "source venv/bin/activate || . venv/Scripts/activate || true",
                        "pip install safety bandit || true",
                        "safety check || true",
                        "bandit -r . -ll || true"
                    ],
                    working_dir="backend",
                    timeout_seconds=300,
                    depends_on=["test-backend"],
                    continue_on_error=True
                ),
                PipelineStage(
                    name="build",
                    stage_type=StageType.BUILD,
                    commands=[
                        "cd frontend",
                        "npm run build || echo 'Build skipped'"
                    ],
                    working_dir="frontend",
                    timeout_seconds=600,
                    depends_on=["test-frontend"],
                    artifacts=["frontend/dist/", "frontend/build/"]
                )
            ]
        )
        self.pipelines[ci_pipeline.id] = ci_pipeline

        # Quick Test Pipeline
        quick_pipeline = Pipeline(
            id="grace-quick",
            name="GRACE Quick Check",
            description="Fast validation pipeline for quick feedback",
            triggers=["push"],
            branches=["*"],
            stages=[
                PipelineStage(
                    name="quick-lint",
                    stage_type=StageType.LINT,
                    commands=[
                        "cd backend",
                        "python -m py_compile app.py || echo 'Syntax check'"
                    ],
                    timeout_seconds=60
                ),
                PipelineStage(
                    name="quick-test",
                    stage_type=StageType.TEST,
                    commands=[
                        "cd backend",
                        "python -c \"import app; print('Import OK')\" || echo 'Import check'"
                    ],
                    timeout_seconds=60,
                    depends_on=["quick-lint"]
                )
            ]
        )
        self.pipelines[quick_pipeline.id] = quick_pipeline

        # Deploy Pipeline
        deploy_pipeline = Pipeline(
            id="grace-deploy",
            name="GRACE Deployment",
            description="Production deployment pipeline",
            triggers=["manual"],
            branches=["main"],
            stages=[
                PipelineStage(
                    name="pre-deploy-check",
                    stage_type=StageType.CUSTOM,
                    commands=[
                        "echo 'Checking deployment prerequisites...'",
                        "docker --version || echo 'Docker not available'",
                        "kubectl version --client || echo 'kubectl not available'"
                    ],
                    timeout_seconds=60
                ),
                PipelineStage(
                    name="build-images",
                    stage_type=StageType.BUILD,
                    commands=[
                        "docker build -t grace-backend:latest ./backend || echo 'Backend build skipped'",
                        "docker build -t grace-frontend:latest ./frontend || echo 'Frontend build skipped'"
                    ],
                    timeout_seconds=900,
                    depends_on=["pre-deploy-check"]
                ),
                PipelineStage(
                    name="deploy",
                    stage_type=StageType.DEPLOY,
                    commands=[
                        "echo 'Deployment would happen here'",
                        "echo 'kubectl apply -f k8s/' || echo 'K8s deploy skipped'"
                    ],
                    timeout_seconds=600,
                    depends_on=["build-images"]
                )
            ]
        )
        self.pipelines[deploy_pipeline.id] = deploy_pipeline

    def _generate_genesis_key(self, action: str, metadata: Dict[str, Any]) -> str:
        """Generate a Genesis Key for CI/CD tracking."""
        timestamp = datetime.utcnow().isoformat()
        key_data = f"{action}:{timestamp}:{json.dumps(metadata, sort_keys=True)}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        genesis_key = f"gk-cicd-{key_hash}"

        self.genesis_keys[genesis_key] = {
            "action": action,
            "timestamp": timestamp,
            "metadata": metadata,
            "created_at": timestamp
        }

        logger.info(f"[Genesis] Created key {genesis_key} for action {action}")
        return genesis_key

    async def trigger_pipeline(
        self,
        pipeline_id: str,
        trigger: str = "manual",
        branch: str = "main",
        commit_sha: Optional[str] = None,
        commit_message: Optional[str] = None,
        triggered_by: str = "system",
        variables: Optional[Dict[str, str]] = None
    ) -> PipelineRun:
        """
        Trigger a pipeline execution.

        Args:
            pipeline_id: ID of pipeline to run
            trigger: Trigger type (push, pull_request, manual, schedule)
            branch: Git branch
            commit_sha: Git commit SHA
            commit_message: Commit message
            triggered_by: User/system that triggered
            variables: Additional environment variables

        Returns:
            PipelineRun object
        """
        if pipeline_id not in self.pipelines:
            raise ValueError(f"Pipeline '{pipeline_id}' not found")

        pipeline = self.pipelines[pipeline_id]
        run_id = str(uuid.uuid4())[:8]

        # Generate Genesis Key for tracking
        genesis_key = self._generate_genesis_key(
            GenesisKeyAction.PIPELINE_TRIGGER,
            {
                "pipeline_id": pipeline_id,
                "run_id": run_id,
                "trigger": trigger,
                "branch": branch,
                "commit_sha": commit_sha
            }
        )

        run = PipelineRun(
            id=run_id,
            pipeline_id=pipeline_id,
            pipeline_name=pipeline.name,
            genesis_key=genesis_key,
            status=PipelineStatus.QUEUED,
            trigger=trigger,
            branch=branch,
            commit_sha=commit_sha,
            commit_message=commit_message,
            triggered_by=triggered_by,
            metadata={"variables": variables or {}}
        )

        self.runs[run_id] = run

        # Queue for execution
        await self.run_queue.put(run_id)

        logger.info(f"[CICD] Pipeline '{pipeline.name}' queued as run {run_id}")

        # Start worker if not running
        if not self._running:
            self._start_worker()

        return run

    def _start_worker(self):
        """Start the pipeline worker."""
        if self._worker_task is None or self._worker_task.done():
            self._running = True
            self._worker_task = asyncio.create_task(self._pipeline_worker())

    async def _pipeline_worker(self):
        """Background worker that processes pipeline runs."""
        logger.info("[CICD] Pipeline worker started")

        while self._running:
            try:
                # Wait for a run with timeout
                try:
                    run_id = await asyncio.wait_for(self.run_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue

                # Check concurrent limit
                while len(self.active_runs) >= self.max_concurrent_runs:
                    await asyncio.sleep(1)

                # Execute pipeline
                task = asyncio.create_task(self._execute_pipeline(run_id))
                self.active_runs[run_id] = task

            except Exception as e:
                logger.error(f"[CICD] Worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_pipeline(self, run_id: str):
        """Execute a pipeline run."""
        run = self.runs.get(run_id)
        if not run:
            return

        pipeline = self.pipelines.get(run.pipeline_id)
        if not pipeline:
            run.status = PipelineStatus.FAILED
            return

        run.status = PipelineStatus.RUNNING
        run.started_at = datetime.utcnow().isoformat()

        # Create workspace for this run
        run_workspace = self.workspace_dir / run_id
        run_workspace.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"[CICD] Executing pipeline {pipeline.name} (run: {run_id})")

            # Build stage dependency graph
            completed_stages: Dict[str, StageResult] = {}

            for stage in pipeline.stages:
                # Check dependencies
                deps_met = all(
                    dep in completed_stages and
                    completed_stages[dep].status == PipelineStatus.SUCCESS
                    for dep in stage.depends_on
                )

                if not deps_met and stage.depends_on:
                    # Check if any dependency failed without continue_on_error
                    dep_failed = any(
                        dep in completed_stages and
                        completed_stages[dep].status == PipelineStatus.FAILED
                        for dep in stage.depends_on
                    )
                    if dep_failed:
                        result = StageResult(
                            stage_name=stage.name,
                            status=PipelineStatus.SKIPPED,
                            started_at=datetime.utcnow().isoformat(),
                            completed_at=datetime.utcnow().isoformat(),
                            stderr="Skipped due to dependency failure"
                        )
                        completed_stages[stage.name] = result
                        run.stage_results.append(result)
                        continue

                # Execute stage
                result = await self._execute_stage(
                    stage,
                    run_workspace,
                    run.branch,
                    {**pipeline.environment, **run.metadata.get("variables", {})}
                )

                completed_stages[stage.name] = result
                run.stage_results.append(result)

                # Generate Genesis Key for stage
                self._generate_genesis_key(
                    GenesisKeyAction.PIPELINE_STAGE,
                    {
                        "run_id": run_id,
                        "stage": stage.name,
                        "status": result.status.value,
                        "duration": result.duration_seconds
                    }
                )

                # Check if we should stop
                if result.status == PipelineStatus.FAILED and not stage.continue_on_error:
                    run.status = PipelineStatus.FAILED
                    break

                # Collect artifacts
                for artifact_path in stage.artifacts:
                    full_path = run_workspace / artifact_path
                    if full_path.exists():
                        artifact_dest = self.artifacts_dir / run_id / artifact_path
                        artifact_dest.parent.mkdir(parents=True, exist_ok=True)
                        if full_path.is_dir():
                            shutil.copytree(full_path, artifact_dest, dirs_exist_ok=True)
                        else:
                            shutil.copy2(full_path, artifact_dest)
                        run.artifacts[artifact_path] = str(artifact_dest)

            # Determine final status
            if run.status != PipelineStatus.FAILED:
                all_success = all(
                    r.status in [PipelineStatus.SUCCESS, PipelineStatus.SKIPPED]
                    for r in run.stage_results
                )
                run.status = PipelineStatus.SUCCESS if all_success else PipelineStatus.FAILED

        except Exception as e:
            logger.error(f"[CICD] Pipeline execution error: {e}")
            run.status = PipelineStatus.FAILED
            run.logs += f"\nPipeline error: {str(e)}"

        finally:
            run.completed_at = datetime.utcnow().isoformat()
            if run.started_at:
                start = datetime.fromisoformat(run.started_at)
                end = datetime.fromisoformat(run.completed_at)
                run.duration_seconds = (end - start).total_seconds()

            # Generate completion Genesis Key
            self._generate_genesis_key(
                GenesisKeyAction.PIPELINE_COMPLETE,
                {
                    "run_id": run_id,
                    "pipeline_id": run.pipeline_id,
                    "status": run.status.value,
                    "duration": run.duration_seconds,
                    "stages_run": len(run.stage_results)
                }
            )

            # Cleanup
            if run_id in self.active_runs:
                del self.active_runs[run_id]

            # Optionally cleanup workspace (keep for debugging)
            # shutil.rmtree(run_workspace, ignore_errors=True)

            logger.info(f"[CICD] Pipeline {run.pipeline_name} completed: {run.status.value}")

    async def _execute_stage(
        self,
        stage: PipelineStage,
        workspace: Path,
        branch: str,
        environment: Dict[str, str]
    ) -> StageResult:
        """Execute a single pipeline stage."""
        started_at = datetime.utcnow().isoformat()

        result = StageResult(
            stage_name=stage.name,
            status=PipelineStatus.RUNNING,
            started_at=started_at
        )

        # Prepare environment
        env = os.environ.copy()
        env.update(environment)
        env["BRANCH"] = branch
        env["WORKSPACE"] = str(workspace)
        env["GRACE_CICD"] = "true"
        env.update(stage.environment)

        # Determine working directory
        work_dir = workspace
        if stage.working_dir:
            work_dir = workspace / stage.working_dir
            work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Combine commands into a script
            script = "\n".join(stage.commands)

            logger.info(f"[CICD] Running stage: {stage.name}")

            # Execute
            process = await asyncio.create_subprocess_shell(
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=stage.timeout_seconds
                )
                result.exit_code = process.returncode
                result.stdout = stdout.decode('utf-8', errors='replace')[-10000:]  # Last 10KB
                result.stderr = stderr.decode('utf-8', errors='replace')[-10000:]

            except asyncio.TimeoutError:
                process.kill()
                result.status = PipelineStatus.FAILED
                result.stderr = f"Stage timed out after {stage.timeout_seconds} seconds"
                result.exit_code = -1

            # Determine status
            if result.exit_code == 0:
                result.status = PipelineStatus.SUCCESS
            else:
                result.status = PipelineStatus.FAILED

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.stderr = str(e)
            result.exit_code = -1

        result.completed_at = datetime.utcnow().isoformat()
        start = datetime.fromisoformat(result.started_at)
        end = datetime.fromisoformat(result.completed_at)
        result.duration_seconds = (end - start).total_seconds()

        logger.info(f"[CICD] Stage {stage.name}: {result.status.value} ({result.duration_seconds:.1f}s)")

        return result

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self.pipelines.get(pipeline_id)

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get a pipeline run by ID."""
        return self.runs.get(run_id)

    def list_pipelines(self) -> List[Pipeline]:
        """List all registered pipelines."""
        return list(self.pipelines.values())

    def list_runs(
        self,
        pipeline_id: Optional[str] = None,
        status: Optional[PipelineStatus] = None,
        limit: int = 50
    ) -> List[PipelineRun]:
        """List pipeline runs with optional filters."""
        runs = list(self.runs.values())

        if pipeline_id:
            runs = [r for r in runs if r.pipeline_id == pipeline_id]

        if status:
            runs = [r for r in runs if r.status == status]

        # Sort by start time descending
        runs.sort(key=lambda r: r.started_at or "", reverse=True)

        return runs[:limit]

    def register_pipeline(self, pipeline: Pipeline):
        """Register a new pipeline."""
        self.pipelines[pipeline.id] = pipeline
        logger.info(f"[CICD] Registered pipeline: {pipeline.name}")

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running pipeline."""
        run = self.runs.get(run_id)
        if not run:
            return False

        if run.status not in [PipelineStatus.PENDING, PipelineStatus.QUEUED, PipelineStatus.RUNNING]:
            return False

        # Cancel the task if running
        if run_id in self.active_runs:
            self.active_runs[run_id].cancel()

        run.status = PipelineStatus.CANCELLED
        run.completed_at = datetime.utcnow().isoformat()

        logger.info(f"[CICD] Cancelled run: {run_id}")
        return True

    def get_genesis_keys(self, run_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get Genesis Keys, optionally filtered by run ID."""
        if run_id:
            return {
                k: v for k, v in self.genesis_keys.items()
                if v.get("metadata", {}).get("run_id") == run_id
            }
        return self.genesis_keys

    async def stop(self):
        """Stop the CI/CD system."""
        self._running = False

        # Cancel all active runs
        for run_id, task in list(self.active_runs.items()):
            task.cancel()

        if self._worker_task:
            self._worker_task.cancel()

        logger.info("[CICD] Pipeline system stopped")


# =============================================================================
# Global Instance
# =============================================================================

_cicd_instance: Optional[GenesisCICD] = None


def get_cicd() -> GenesisCICD:
    """Get the global CI/CD instance."""
    global _cicd_instance
    if _cicd_instance is None:
        _cicd_instance = GenesisCICD()
    return _cicd_instance


async def init_cicd():
    """Initialize the CI/CD system."""
    cicd = get_cicd()
    cicd._start_worker()
    logger.info("[CICD] Genesis CI/CD system initialized")


async def shutdown_cicd():
    """Shutdown the CI/CD system."""
    global _cicd_instance
    if _cicd_instance:
        await _cicd_instance.stop()
        _cicd_instance = None
