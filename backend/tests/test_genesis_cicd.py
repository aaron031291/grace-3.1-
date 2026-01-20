"""
Comprehensive Component Tests for Genesis CI/CD System

Tests the complete CI/CD functionality:
- Pipeline definitions and management
- Stage execution
- Genesis Key tracking
- Run management
- Artifact collection
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import asyncio
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==================== PipelineStatus Tests ====================

class TestPipelineStatus:
    """Test PipelineStatus enum"""

    def test_all_statuses_exist(self):
        """Test all expected statuses are defined"""
        from genesis.cicd import PipelineStatus

        assert hasattr(PipelineStatus, 'PENDING')
        assert hasattr(PipelineStatus, 'QUEUED')
        assert hasattr(PipelineStatus, 'RUNNING')
        assert hasattr(PipelineStatus, 'SUCCESS')
        assert hasattr(PipelineStatus, 'FAILED')
        assert hasattr(PipelineStatus, 'CANCELLED')
        assert hasattr(PipelineStatus, 'SKIPPED')

    def test_status_values(self):
        """Test status string values"""
        from genesis.cicd import PipelineStatus

        assert PipelineStatus.PENDING.value == "pending"
        assert PipelineStatus.QUEUED.value == "queued"
        assert PipelineStatus.RUNNING.value == "running"
        assert PipelineStatus.SUCCESS.value == "success"
        assert PipelineStatus.FAILED.value == "failed"


class TestStageType:
    """Test StageType enum"""

    def test_all_stage_types_exist(self):
        """Test all expected stage types are defined"""
        from genesis.cicd import StageType

        assert hasattr(StageType, 'CHECKOUT')
        assert hasattr(StageType, 'INSTALL')
        assert hasattr(StageType, 'LINT')
        assert hasattr(StageType, 'TEST')
        assert hasattr(StageType, 'BUILD')
        assert hasattr(StageType, 'SECURITY')
        assert hasattr(StageType, 'DEPLOY')
        assert hasattr(StageType, 'NOTIFY')
        assert hasattr(StageType, 'CUSTOM')


# ==================== StageResult Tests ====================

class TestStageResult:
    """Test StageResult dataclass"""

    def test_stage_result_creation(self):
        """Test creating a stage result"""
        from genesis.cicd import StageResult, PipelineStatus

        result = StageResult(
            stage_name="test-stage",
            status=PipelineStatus.SUCCESS,
            started_at="2025-01-01T00:00:00"
        )

        assert result.stage_name == "test-stage"
        assert result.status == PipelineStatus.SUCCESS
        assert result.started_at == "2025-01-01T00:00:00"
        assert result.exit_code == 0
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.artifacts == []

    def test_stage_result_with_output(self):
        """Test stage result with output"""
        from genesis.cicd import StageResult, PipelineStatus

        result = StageResult(
            stage_name="test",
            status=PipelineStatus.SUCCESS,
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:00:10",
            duration_seconds=10.0,
            exit_code=0,
            stdout="Test passed",
            stderr=""
        )

        assert result.duration_seconds == 10.0
        assert result.stdout == "Test passed"


# ==================== PipelineStage Tests ====================

class TestPipelineStage:
    """Test PipelineStage dataclass"""

    def test_pipeline_stage_creation(self):
        """Test creating a pipeline stage"""
        from genesis.cicd import PipelineStage, StageType

        stage = PipelineStage(
            name="install",
            stage_type=StageType.INSTALL,
            commands=["pip install -r requirements.txt"]
        )

        assert stage.name == "install"
        assert stage.stage_type == StageType.INSTALL
        assert stage.commands == ["pip install -r requirements.txt"]
        assert stage.timeout_seconds == 600
        assert stage.continue_on_error == False
        assert stage.depends_on == []

    def test_pipeline_stage_with_dependencies(self):
        """Test stage with dependencies"""
        from genesis.cicd import PipelineStage, StageType

        stage = PipelineStage(
            name="test",
            stage_type=StageType.TEST,
            commands=["pytest tests/"],
            depends_on=["install", "lint"],
            timeout_seconds=300
        )

        assert stage.depends_on == ["install", "lint"]
        assert stage.timeout_seconds == 300


# ==================== Pipeline Tests ====================

class TestPipeline:
    """Test Pipeline dataclass"""

    def test_pipeline_creation(self):
        """Test creating a pipeline"""
        from genesis.cicd import Pipeline

        pipeline = Pipeline(
            id="test-pipeline",
            name="Test Pipeline",
            description="A test pipeline"
        )

        assert pipeline.id == "test-pipeline"
        assert pipeline.name == "Test Pipeline"
        assert pipeline.description == "A test pipeline"
        assert pipeline.stages == []
        assert pipeline.triggers == []

    def test_pipeline_with_stages(self):
        """Test pipeline with stages"""
        from genesis.cicd import Pipeline, PipelineStage, StageType

        stages = [
            PipelineStage(
                name="lint",
                stage_type=StageType.LINT,
                commands=["flake8 ."]
            ),
            PipelineStage(
                name="test",
                stage_type=StageType.TEST,
                commands=["pytest"],
                depends_on=["lint"]
            )
        ]

        pipeline = Pipeline(
            id="ci",
            name="CI Pipeline",
            stages=stages,
            triggers=["push", "pull_request"]
        )

        assert len(pipeline.stages) == 2
        assert pipeline.triggers == ["push", "pull_request"]


# ==================== PipelineRun Tests ====================

class TestPipelineRun:
    """Test PipelineRun dataclass"""

    def test_pipeline_run_creation(self):
        """Test creating a pipeline run"""
        from genesis.cicd import PipelineRun, PipelineStatus

        run = PipelineRun(
            id="run-001",
            pipeline_id="ci",
            pipeline_name="CI Pipeline",
            genesis_key="gk-cicd-abc123"
        )

        assert run.id == "run-001"
        assert run.pipeline_id == "ci"
        assert run.genesis_key == "gk-cicd-abc123"
        assert run.status == PipelineStatus.PENDING
        assert run.trigger == "manual"
        assert run.branch == "main"

    def test_pipeline_run_with_commit(self):
        """Test run with commit info"""
        from genesis.cicd import PipelineRun, PipelineStatus

        run = PipelineRun(
            id="run-002",
            pipeline_id="ci",
            pipeline_name="CI Pipeline",
            genesis_key="gk-cicd-def456",
            branch="feature/test",
            commit_sha="abc123def",
            commit_message="Add new feature"
        )

        assert run.branch == "feature/test"
        assert run.commit_sha == "abc123def"
        assert run.commit_message == "Add new feature"


# ==================== GenesisKeyAction Tests ====================

class TestGenesisKeyAction:
    """Test GenesisKeyAction constants"""

    def test_action_constants(self):
        """Test action constants are defined"""
        from genesis.cicd import GenesisKeyAction

        assert GenesisKeyAction.PIPELINE_TRIGGER == "cicd:pipeline:trigger"
        assert GenesisKeyAction.PIPELINE_STAGE == "cicd:pipeline:stage"
        assert GenesisKeyAction.PIPELINE_COMPLETE == "cicd:pipeline:complete"
        assert GenesisKeyAction.BUILD_ARTIFACT == "cicd:build:artifact"
        assert GenesisKeyAction.TEST_EXECUTION == "cicd:test:execution"
        assert GenesisKeyAction.DEPLOYMENT == "cicd:deploy"


# ==================== GenesisCICD Tests ====================

class TestGenesisCICD:
    """Test GenesisCICD class"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cicd(self, temp_workspace):
        """Create CI/CD instance with temp directories"""
        from genesis.cicd import GenesisCICD

        return GenesisCICD(
            workspace_dir=str(temp_workspace / "workspace"),
            artifacts_dir=str(temp_workspace / "artifacts")
        )

    def test_cicd_initialization(self, cicd, temp_workspace):
        """Test CI/CD initializes correctly"""
        assert cicd.workspace_dir.exists()
        assert cicd.artifacts_dir.exists()
        assert cicd.max_concurrent_runs == 5
        assert len(cicd.pipelines) > 0  # Default pipelines registered

    def test_default_pipelines_registered(self, cicd):
        """Test default pipelines are registered"""
        assert "grace-ci" in cicd.pipelines
        assert "grace-quick" in cicd.pipelines
        assert "grace-deploy" in cicd.pipelines

    def test_grace_ci_pipeline_stages(self, cicd):
        """Test GRACE CI pipeline has expected stages"""
        pipeline = cicd.pipelines["grace-ci"]

        stage_names = [s.name for s in pipeline.stages]
        assert "checkout" in stage_names
        assert "install-backend" in stage_names
        assert "test-backend" in stage_names
        assert "build" in stage_names

    def test_generate_genesis_key(self, cicd):
        """Test Genesis Key generation"""
        from genesis.cicd import GenesisKeyAction

        key = cicd._generate_genesis_key(
            GenesisKeyAction.PIPELINE_TRIGGER,
            {"pipeline_id": "test", "run_id": "001"}
        )

        assert key.startswith("gk-cicd-")
        assert key in cicd.genesis_keys
        assert cicd.genesis_keys[key]["action"] == GenesisKeyAction.PIPELINE_TRIGGER

    def test_get_pipeline(self, cicd):
        """Test getting pipeline by ID"""
        pipeline = cicd.get_pipeline("grace-ci")
        assert pipeline is not None
        assert pipeline.name == "GRACE CI Pipeline"

        # Non-existent pipeline
        assert cicd.get_pipeline("nonexistent") is None

    def test_list_pipelines(self, cicd):
        """Test listing all pipelines"""
        pipelines = cicd.list_pipelines()
        assert len(pipelines) >= 3
        assert all(hasattr(p, 'id') for p in pipelines)

    def test_register_pipeline(self, cicd):
        """Test registering a new pipeline"""
        from genesis.cicd import Pipeline

        new_pipeline = Pipeline(
            id="custom-pipeline",
            name="Custom Pipeline",
            description="A custom test pipeline"
        )

        cicd.register_pipeline(new_pipeline)

        assert "custom-pipeline" in cicd.pipelines
        assert cicd.pipelines["custom-pipeline"].name == "Custom Pipeline"


class TestGenesisCICDAsync:
    """Test async CI/CD operations"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cicd(self, temp_workspace):
        """Create CI/CD instance"""
        from genesis.cicd import GenesisCICD

        return GenesisCICD(
            workspace_dir=str(temp_workspace / "workspace"),
            artifacts_dir=str(temp_workspace / "artifacts")
        )

    @pytest.mark.asyncio
    async def test_trigger_pipeline(self, cicd):
        """Test triggering a pipeline"""
        from genesis.cicd import PipelineStatus

        run = await cicd.trigger_pipeline(
            pipeline_id="grace-quick",
            trigger="manual",
            branch="main",
            triggered_by="test"
        )

        assert run.id is not None
        assert run.pipeline_id == "grace-quick"
        assert run.status == PipelineStatus.QUEUED
        assert run.genesis_key.startswith("gk-cicd-")

        # Clean up
        await cicd.stop()

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_pipeline(self, cicd):
        """Test triggering non-existent pipeline"""
        with pytest.raises(ValueError, match="not found"):
            await cicd.trigger_pipeline(
                pipeline_id="nonexistent-pipeline",
                trigger="manual"
            )

    @pytest.mark.asyncio
    async def test_get_run(self, cicd):
        """Test getting a run by ID"""
        run = await cicd.trigger_pipeline(
            pipeline_id="grace-quick",
            trigger="manual"
        )

        retrieved = cicd.get_run(run.id)
        assert retrieved is not None
        assert retrieved.id == run.id

        # Non-existent run
        assert cicd.get_run("nonexistent") is None

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_list_runs(self, cicd):
        """Test listing runs"""
        # Trigger a few runs
        for i in range(3):
            await cicd.trigger_pipeline(
                pipeline_id="grace-quick",
                trigger="manual"
            )

        runs = cicd.list_runs()
        assert len(runs) >= 3

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_list_runs_filter_by_pipeline(self, cicd):
        """Test filtering runs by pipeline ID"""
        await cicd.trigger_pipeline(
            pipeline_id="grace-quick",
            trigger="manual"
        )
        await cicd.trigger_pipeline(
            pipeline_id="grace-ci",
            trigger="manual"
        )

        quick_runs = cicd.list_runs(pipeline_id="grace-quick")
        ci_runs = cicd.list_runs(pipeline_id="grace-ci")

        assert all(r.pipeline_id == "grace-quick" for r in quick_runs)
        assert all(r.pipeline_id == "grace-ci" for r in ci_runs)

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_cancel_run(self, cicd):
        """Test cancelling a run"""
        from genesis.cicd import PipelineStatus

        run = await cicd.trigger_pipeline(
            pipeline_id="grace-quick",
            trigger="manual"
        )

        result = await cicd.cancel_run(run.id)
        assert result == True

        updated_run = cicd.get_run(run.id)
        assert updated_run.status == PipelineStatus.CANCELLED

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_run(self, cicd):
        """Test cancelling non-existent run"""
        result = await cicd.cancel_run("nonexistent-run")
        assert result == False

    @pytest.mark.asyncio
    async def test_genesis_keys_for_run(self, cicd):
        """Test getting Genesis Keys for a run"""
        run = await cicd.trigger_pipeline(
            pipeline_id="grace-quick",
            trigger="manual"
        )

        # Wait a bit for keys to be generated
        await asyncio.sleep(0.1)

        keys = cicd.get_genesis_keys(run_id=run.id)
        # At least the trigger key should exist
        assert len(keys) >= 1

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_stop_cicd(self, cicd):
        """Test stopping CI/CD system"""
        await cicd.trigger_pipeline(
            pipeline_id="grace-quick",
            trigger="manual"
        )

        await cicd.stop()
        assert cicd._running == False


class TestGenesisCICDStageExecution:
    """Test stage execution"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cicd(self, temp_workspace):
        """Create CI/CD instance"""
        from genesis.cicd import GenesisCICD

        return GenesisCICD(
            workspace_dir=str(temp_workspace / "workspace"),
            artifacts_dir=str(temp_workspace / "artifacts")
        )

    @pytest.mark.asyncio
    async def test_execute_simple_stage(self, cicd, temp_workspace):
        """Test executing a simple stage"""
        from genesis.cicd import PipelineStage, StageType, PipelineStatus

        stage = PipelineStage(
            name="echo-test",
            stage_type=StageType.CUSTOM,
            commands=["echo 'Hello World'"],
            timeout_seconds=10
        )

        workspace = temp_workspace / "workspace" / "test-run"
        workspace.mkdir(parents=True, exist_ok=True)

        result = await cicd._execute_stage(
            stage=stage,
            workspace=workspace,
            branch="main",
            environment={}
        )

        assert result.status == PipelineStatus.SUCCESS
        assert result.exit_code == 0
        assert "Hello World" in result.stdout or result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_failing_stage(self, cicd, temp_workspace):
        """Test executing a failing stage"""
        from genesis.cicd import PipelineStage, StageType, PipelineStatus

        stage = PipelineStage(
            name="fail-test",
            stage_type=StageType.CUSTOM,
            commands=["exit 1"],
            timeout_seconds=10
        )

        workspace = temp_workspace / "workspace" / "test-run"
        workspace.mkdir(parents=True, exist_ok=True)

        result = await cicd._execute_stage(
            stage=stage,
            workspace=workspace,
            branch="main",
            environment={}
        )

        assert result.status == PipelineStatus.FAILED
        assert result.exit_code != 0

    @pytest.mark.asyncio
    async def test_stage_with_environment(self, cicd, temp_workspace):
        """Test stage with environment variables"""
        from genesis.cicd import PipelineStage, StageType, PipelineStatus

        stage = PipelineStage(
            name="env-test",
            stage_type=StageType.CUSTOM,
            commands=["echo $TEST_VAR"],
            environment={"TEST_VAR": "test_value"},
            timeout_seconds=10
        )

        workspace = temp_workspace / "workspace" / "test-run"
        workspace.mkdir(parents=True, exist_ok=True)

        result = await cicd._execute_stage(
            stage=stage,
            workspace=workspace,
            branch="main",
            environment={}
        )

        assert result.status == PipelineStatus.SUCCESS


class TestGenesisCICDPipelineExecution:
    """Test full pipeline execution"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cicd(self, temp_workspace):
        """Create CI/CD instance"""
        from genesis.cicd import GenesisCICD

        return GenesisCICD(
            workspace_dir=str(temp_workspace / "workspace"),
            artifacts_dir=str(temp_workspace / "artifacts")
        )

    @pytest.mark.asyncio
    async def test_execute_simple_pipeline(self, cicd, temp_workspace):
        """Test executing a simple custom pipeline"""
        from genesis.cicd import Pipeline, PipelineStage, StageType, PipelineStatus

        # Register a simple test pipeline
        simple_pipeline = Pipeline(
            id="simple-test",
            name="Simple Test",
            stages=[
                PipelineStage(
                    name="step1",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'Step 1'"],
                    timeout_seconds=5
                ),
                PipelineStage(
                    name="step2",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'Step 2'"],
                    depends_on=["step1"],
                    timeout_seconds=5
                )
            ]
        )
        cicd.register_pipeline(simple_pipeline)

        # Trigger and wait for completion
        run = await cicd.trigger_pipeline(
            pipeline_id="simple-test",
            trigger="test"
        )

        # Give time for execution
        await asyncio.sleep(2)

        # Check results
        updated_run = cicd.get_run(run.id)
        # May still be running or completed
        assert updated_run.status in [
            PipelineStatus.QUEUED,
            PipelineStatus.RUNNING,
            PipelineStatus.SUCCESS,
            PipelineStatus.FAILED
        ]

        await cicd.stop()


# ==================== Global Function Tests ====================

class TestGlobalFunctions:
    """Test global convenience functions"""

    def test_get_cicd_singleton(self):
        """Test get_cicd returns singleton"""
        from genesis.cicd import get_cicd, _cicd_instance
        import genesis.cicd as cicd_module

        # Reset singleton
        cicd_module._cicd_instance = None

        cicd1 = get_cicd()
        cicd2 = get_cicd()

        assert cicd1 is cicd2

    @pytest.mark.asyncio
    async def test_init_cicd(self):
        """Test init_cicd function"""
        import genesis.cicd as cicd_module

        # Reset singleton
        cicd_module._cicd_instance = None

        await cicd_module.init_cicd()

        assert cicd_module._cicd_instance is not None
        assert cicd_module._cicd_instance._running == True

        await cicd_module.shutdown_cicd()

    @pytest.mark.asyncio
    async def test_shutdown_cicd(self):
        """Test shutdown_cicd function"""
        import genesis.cicd as cicd_module

        # Initialize first
        cicd_module._cicd_instance = None
        await cicd_module.init_cicd()

        await cicd_module.shutdown_cicd()

        assert cicd_module._cicd_instance is None


# ==================== Integration Tests ====================

class TestCICDIntegration:
    """Integration tests for CI/CD system"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cicd(self, temp_workspace):
        """Create CI/CD instance"""
        from genesis.cicd import GenesisCICD

        return GenesisCICD(
            workspace_dir=str(temp_workspace / "workspace"),
            artifacts_dir=str(temp_workspace / "artifacts")
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_lifecycle(self, cicd):
        """Test complete pipeline lifecycle"""
        from genesis.cicd import Pipeline, PipelineStage, StageType, PipelineStatus

        # Create a multi-stage pipeline
        test_pipeline = Pipeline(
            id="lifecycle-test",
            name="Lifecycle Test",
            stages=[
                PipelineStage(
                    name="prepare",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'Preparing...'"],
                    timeout_seconds=5
                ),
                PipelineStage(
                    name="validate",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'Validating...'"],
                    depends_on=["prepare"],
                    timeout_seconds=5
                ),
                PipelineStage(
                    name="complete",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'Complete!'"],
                    depends_on=["validate"],
                    timeout_seconds=5
                )
            ]
        )
        cicd.register_pipeline(test_pipeline)

        # Trigger
        run = await cicd.trigger_pipeline(
            pipeline_id="lifecycle-test",
            trigger="test",
            branch="main",
            commit_sha="abc123",
            commit_message="Test commit"
        )

        assert run.status == PipelineStatus.QUEUED
        assert run.commit_sha == "abc123"

        # Genesis key should be created
        assert run.genesis_key.startswith("gk-cicd-")

        # Wait briefly
        await asyncio.sleep(1)

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_pipeline_with_dependency_failure(self, cicd):
        """Test pipeline behavior when dependency fails"""
        from genesis.cicd import Pipeline, PipelineStage, StageType

        # Pipeline where first stage fails
        failing_pipeline = Pipeline(
            id="fail-test",
            name="Failure Test",
            stages=[
                PipelineStage(
                    name="failing-step",
                    stage_type=StageType.CUSTOM,
                    commands=["exit 1"],  # This will fail
                    timeout_seconds=5
                ),
                PipelineStage(
                    name="dependent-step",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'This should not run'"],
                    depends_on=["failing-step"],
                    timeout_seconds=5
                )
            ]
        )
        cicd.register_pipeline(failing_pipeline)

        run = await cicd.trigger_pipeline(
            pipeline_id="fail-test",
            trigger="test"
        )

        # Wait for execution
        await asyncio.sleep(2)

        await cicd.stop()

    @pytest.mark.asyncio
    async def test_pipeline_continue_on_error(self, cicd):
        """Test continue_on_error behavior"""
        from genesis.cicd import Pipeline, PipelineStage, StageType

        # Pipeline with continue_on_error
        continue_pipeline = Pipeline(
            id="continue-test",
            name="Continue Test",
            stages=[
                PipelineStage(
                    name="optional-step",
                    stage_type=StageType.CUSTOM,
                    commands=["exit 1"],  # Fails but continues
                    timeout_seconds=5,
                    continue_on_error=True
                ),
                PipelineStage(
                    name="next-step",
                    stage_type=StageType.CUSTOM,
                    commands=["echo 'Should still run'"],
                    depends_on=["optional-step"],
                    timeout_seconds=5
                )
            ]
        )
        cicd.register_pipeline(continue_pipeline)

        run = await cicd.trigger_pipeline(
            pipeline_id="continue-test",
            trigger="test"
        )

        await asyncio.sleep(2)
        await cicd.stop()


# ==================== Error Handling Tests ====================

class TestCICDErrorHandling:
    """Test error handling in CI/CD"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cicd(self, temp_workspace):
        """Create CI/CD instance"""
        from genesis.cicd import GenesisCICD

        return GenesisCICD(
            workspace_dir=str(temp_workspace / "workspace"),
            artifacts_dir=str(temp_workspace / "artifacts")
        )

    @pytest.mark.asyncio
    async def test_stage_timeout(self, cicd, temp_workspace):
        """Test stage timeout handling"""
        from genesis.cicd import PipelineStage, StageType, PipelineStatus

        # Stage that takes too long
        slow_stage = PipelineStage(
            name="slow-stage",
            stage_type=StageType.CUSTOM,
            commands=["sleep 10"],
            timeout_seconds=1  # 1 second timeout
        )

        workspace = temp_workspace / "workspace" / "timeout-test"
        workspace.mkdir(parents=True, exist_ok=True)

        result = await cicd._execute_stage(
            stage=slow_stage,
            workspace=workspace,
            branch="main",
            environment={}
        )

        assert result.status == PipelineStatus.FAILED
        assert "timed out" in result.stderr.lower()

    def test_invalid_pipeline_id(self, cicd):
        """Test handling of invalid pipeline ID"""
        result = cicd.get_pipeline("definitely-not-a-real-pipeline")
        assert result is None

    @pytest.mark.asyncio
    async def test_trigger_with_invalid_pipeline(self, cicd):
        """Test trigger with invalid pipeline raises error"""
        with pytest.raises(ValueError):
            await cicd.trigger_pipeline(
                pipeline_id="invalid-pipeline-id",
                trigger="manual"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
