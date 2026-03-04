"""
Grace Internal Pipeline Runner
===============================
Replaces GitHub Actions — no third-party CI/CD dependency.

Runs pipelines defined in YAML or code, scoped to workspaces.
Grace triggers pipelines autonomously (on file change, on schedule,
on healing events) or manually via API.

Pipeline stages execute in subprocess with timeout and artifact capture.
Results are tracked via Genesis Keys and stored in the database.
"""

import asyncio
import subprocess
import os
import uuid
import yaml
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

from models.workspace_models import PipelineRun, Workspace
from database.session import session_scope

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    name: str
    status: str = "pending"
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class PipelineConfig:
    name: str
    stages: List[Dict[str, Any]]
    trigger: str = "manual"
    working_dir: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 600


class InternalPipelineRunner:
    """
    Runs CI/CD pipelines internally — no GitHub Actions needed.
    """

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id

    def _get_workspace(self, session) -> Workspace:
        ws = session.query(Workspace).filter_by(workspace_id=self.workspace_id).first()
        if not ws:
            raise ValueError(f"Workspace '{self.workspace_id}' not found")
        return ws

    def load_pipeline_yaml(self, yaml_path: str) -> PipelineConfig:
        """Load a pipeline definition from a YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Pipeline file not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        stages = []
        for stage_def in data.get("stages", data.get("pipeline", {}).get("stages", [])):
            stages.append({
                "name": stage_def.get("name", "unnamed"),
                "commands": stage_def.get("commands", stage_def.get("script", [])),
                "working_dir": stage_def.get("working_dir"),
                "timeout": stage_def.get("timeout", 300),
                "continue_on_error": stage_def.get("continue_on_error", False),
            })

        return PipelineConfig(
            name=data.get("name", path.stem),
            stages=stages,
            trigger=data.get("trigger", "manual"),
            working_dir=data.get("working_dir"),
            environment=data.get("environment", {}),
        )

    async def run_pipeline(
        self,
        config: PipelineConfig,
        trigger: str = "manual",
        triggered_by: str = "grace",
        genesis_key_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a full pipeline. Returns the run result."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        with session_scope() as session:
            ws = self._get_workspace(session)
            working_dir = config.working_dir or ws.root_path

            pr = PipelineRun(
                workspace_id=ws.id,
                run_id=run_id,
                pipeline_name=config.name,
                trigger=trigger,
                status="running",
                started_at=datetime.now(timezone.utc),
                config={"stages": [s["name"] for s in config.stages]},
                triggered_by=triggered_by,
                genesis_key_id=genesis_key_id,
            )
            session.add(pr)
            ws.total_pipeline_runs = (ws.total_pipeline_runs or 0) + 1
            session.flush()
            pr_id = pr.id

        stage_results = []
        overall_status = "success"

        for stage_def in config.stages:
            result = await self._run_stage(
                stage_def,
                working_dir=working_dir,
                environment=config.environment,
            )
            stage_results.append(asdict(result))

            if result.status == "failed" and not stage_def.get("continue_on_error"):
                overall_status = "failed"
                break

        completed_at = datetime.now(timezone.utc)

        with session_scope() as session:
            pr = session.query(PipelineRun).filter_by(id=pr_id).first()
            if pr:
                pr.status = overall_status
                pr.completed_at = completed_at
                pr.stages = stage_results
                if pr.started_at:
                    started = pr.started_at.replace(tzinfo=None) if pr.started_at.tzinfo else pr.started_at
                    pr.duration_seconds = (completed_at.replace(tzinfo=None) - started).total_seconds()
                if overall_status == "failed":
                    failed = [s for s in stage_results if s["status"] == "failed"]
                    if failed:
                        pr.error_message = failed[0].get("stderr", "")[:2000]

        logger.info(
            f"[Pipeline] {self.workspace_id}/{config.name} "
            f"run={run_id} status={overall_status} "
            f"stages={len(stage_results)}"
        )

        return {
            "run_id": run_id,
            "pipeline": config.name,
            "workspace": self.workspace_id,
            "status": overall_status,
            "stages": stage_results,
            "trigger": trigger,
        }

    async def _run_stage(
        self,
        stage_def: Dict[str, Any],
        working_dir: str,
        environment: Dict[str, str],
    ) -> StageResult:
        """Run a single pipeline stage."""
        name = stage_def.get("name", "unnamed")
        commands = stage_def.get("commands", [])
        stage_dir = stage_def.get("working_dir") or working_dir
        timeout = stage_def.get("timeout", 300)

        if isinstance(commands, str):
            commands = [commands]

        result = StageResult(
            name=name,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        combined_cmd = " && ".join(commands)
        if not combined_cmd:
            result.status = "skipped"
            result.completed_at = datetime.now(timezone.utc).isoformat()
            return result

        env = {**os.environ, **environment}
        start = datetime.now(timezone.utc)

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    combined_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=stage_dir,
                    env=env,
                ),
                timeout=5,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            result.exit_code = proc.returncode or 0
            result.stdout = stdout.decode("utf-8", errors="replace")[:10000]
            result.stderr = stderr.decode("utf-8", errors="replace")[:10000]
            result.status = "success" if result.exit_code == 0 else "failed"

        except asyncio.TimeoutError:
            result.status = "failed"
            result.stderr = f"Stage timed out after {timeout}s"
            result.exit_code = -1
        except Exception as e:
            result.status = "failed"
            result.stderr = str(e)[:2000]
            result.exit_code = -1

        end = datetime.now(timezone.utc)
        result.duration_seconds = (end - start).total_seconds()
        result.completed_at = end.isoformat()

        return result

    def get_run_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get pipeline run history for this workspace."""
        with session_scope() as session:
            ws = self._get_workspace(session)
            runs = (
                session.query(PipelineRun)
                .filter_by(workspace_id=ws.id)
                .order_by(PipelineRun.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "run_id": r.run_id,
                    "pipeline": r.pipeline_name,
                    "status": r.status,
                    "trigger": r.trigger,
                    "triggered_by": r.triggered_by,
                    "duration_seconds": r.duration_seconds,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "stages": r.stages or [],
                }
                for r in runs
            ]


def get_pipeline_runner(workspace_id: str) -> InternalPipelineRunner:
    """Get the pipeline runner for a workspace."""
    return InternalPipelineRunner(workspace_id)
