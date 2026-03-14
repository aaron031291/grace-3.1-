import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.genesis.cicd import GenesisCICD, PipelineStatus, Pipeline, PipelineStage, StageType

@pytest.fixture
def cicd(tmp_path):
    # Use tmp_path for workspaces to avoid actually creating folders
    workspace = tmp_path / "workspace"
    artifacts = tmp_path / "artifacts"
    
    system = GenesisCICD(
        workspace_dir=str(workspace),
        artifacts_dir=str(artifacts),
        max_concurrent_runs=2
    )
    yield system

@pytest.mark.asyncio
async def test_trigger_pipeline(cicd):
    run = await cicd.trigger_pipeline('grace-quick', trigger='manual')
    
    assert run.pipeline_id == 'grace-quick'
    assert run.status == PipelineStatus.QUEUED
    assert run.id in cicd.runs
    
    # Check if Genesis key was generated
    keys = cicd.get_genesis_keys(run.id)
    assert len(keys) > 0
    assert list(keys.values())[0]["action"] == "cicd:pipeline:trigger"

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_shell')
async def test_execute_pipeline(mock_shell, cicd):
    # Mock subprocess execution
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b'stdout', b'stderr')
    mock_process.returncode = 0
    mock_shell.return_value = mock_process
    
    run = await cicd.trigger_pipeline('grace-quick', trigger='integration-test')
    await cicd._execute_pipeline(run.id)
    
    assert run.status == PipelineStatus.SUCCESS
    assert len(run.stage_results) == 2  # grace-quick has 2 stages
    
    # 2 stages + 1 completion = 3 keys minimum per run
    keys = cicd.get_genesis_keys(run.id)
    actions = [v["action"] for v in keys.values()]
    assert "cicd:pipeline:stage" in actions
    assert "cicd:pipeline:complete" in actions

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_shell')
async def test_execute_pipeline_failure(mock_shell, cicd):
    # Mock subprocess failure
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b'err', b'err')
    mock_process.returncode = 1
    mock_shell.return_value = mock_process
    
    run = await cicd.trigger_pipeline('grace-quick')
    await cicd._execute_pipeline(run.id)
    
    assert run.status == PipelineStatus.FAILED
    assert run.stage_results[0].status == PipelineStatus.FAILED
    # Execution breaks immediately on failure lacking continue_on_error
    assert len(run.stage_results) == 1

@pytest.mark.asyncio
async def test_cancel_run(cicd):
    run = await cicd.trigger_pipeline('grace-quick')
    assert run.status == PipelineStatus.QUEUED
    
    success = await cicd.cancel_run(run.id)
    assert success is True
    assert run.status == PipelineStatus.CANCELLED

if __name__ == "__main__":
    pytest.main(['-v', __file__])
