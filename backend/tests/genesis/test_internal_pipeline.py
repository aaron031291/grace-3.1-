import pytest
import asyncio
import yaml
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from genesis.internal_pipeline import InternalPipelineRunner, PipelineConfig

@pytest.fixture
def mock_session():
    session = MagicMock()
    # Mock context manager
    session.__enter__.return_value = session
    return session

@pytest.fixture
def runner(mock_session):
    with patch('genesis.internal_pipeline.session_scope') as mock_scope:
        mock_scope.return_value.__enter__.return_value = mock_session
        
        # Mock workspace query
        mock_ws = MagicMock()
        mock_ws.root_path = "/tmp"
        mock_ws.id = "ws-id"
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_ws
        
        r = InternalPipelineRunner(workspace_id="ws-123")
        yield r

def test_load_pipeline_yaml(runner, tmp_path):
    # Create temp YAML file
    yaml_config = {
        "name": "Test Pipeline",
        "stages": [
            {
                "name": "build",
                "commands": ["echo foo"]
            }
        ]
    }
    yaml_file = tmp_path / "pipeline.yml"
    with open(yaml_file, "w") as f:
        yaml.dump(yaml_config, f)
        
    config = runner.load_pipeline_yaml(str(yaml_file))
    
    assert config.name == "Test Pipeline"
    assert len(config.stages) == 1
    assert config.stages[0]["name"] == "build"
    assert config.stages[0]["commands"] == ["echo foo"]

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_shell')
async def test_run_pipeline(mock_shell, runner):
    # Mock subprocess success
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b'stdout output', b'stderr output')
    mock_process.returncode = 0
    mock_shell.return_value = mock_process
    
    config = PipelineConfig(
        name="test-run",
        stages=[
            {"name": "test-stage", "commands": ["python -c 'print(1)'"]}
        ]
    )
    
    result = await runner.run_pipeline(config)
    
    assert result["pipeline"] == "test-run"
    assert result["status"] == "success"
    assert result["workspace"] == "ws-123"
    assert len(result["stages"]) == 1
    
    stage = result["stages"][0]
    assert stage["name"] == "test-stage"
    assert stage["status"] == "success"
    assert stage["stdout"] == "stdout output"

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_shell')
async def test_run_pipeline_failure(mock_shell, runner):
    # Mock subprocess failure
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b'', b'error occurred')
    mock_process.returncode = 1
    mock_shell.return_value = mock_process
    
    config = PipelineConfig(
        name="fail-run",
        stages=[
            {"name": "fail-stage", "commands": ["exit 1"]}
        ]
    )
    
    result = await runner.run_pipeline(config)
    
    assert result["status"] == "failed"
    assert result["stages"][0]["status"] == "failed"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
