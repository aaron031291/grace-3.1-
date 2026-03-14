import pytest
import os
import json
from pathlib import Path
from backend.genesis.cicd_versioning import CICDVersionControl, MutationType

@pytest.fixture
def temp_vc(tmp_path):
    storage_dir = tmp_path / "vc"
    vc = CICDVersionControl(storage_dir=str(storage_dir))
    return vc, storage_dir

def test_record_mutation_create(temp_vc):
    vc, storage_dir = temp_vc
    
    config = {"steps": ["test", "build"]}
    version = vc.record_mutation("pipe1", MutationType.CREATE, config, "admin")
    
    assert version.pipeline_id == "pipe1"
    assert version.version_number == 1
    assert version.mutation_type == MutationType.CREATE
    assert version.author == "admin"
    assert "gk-vc-" in version.genesis_key
    
    # Verify saved
    assert (storage_dir / "pipe1" / "history.json").exists()
    assert (storage_dir / "pipe1" / "versions" / "v1.json").exists()

def test_get_version(temp_vc):
    vc, storage_dir = temp_vc
    
    config1 = {"steps": ["test"]}
    vc.record_mutation("pipe1", MutationType.CREATE, config1)
    
    config2 = {"steps": ["test", "deploy"]}
    vc.record_mutation("pipe1", MutationType.UPDATE, config2)
    
    v1 = vc.get_version("pipe1", 1)
    assert v1.version_number == 1
    assert v1.config_snapshot == config1
    
    v_latest = vc.get_version("pipe1")
    assert v_latest.version_number == 2
    assert v_latest.config_snapshot == config2

def test_get_history(temp_vc):
    vc, storage_dir = temp_vc
    
    assert vc.get_history("pipe_nonexistent") == []
    
    vc.record_mutation("pipe1", MutationType.CREATE, {"a": 1})
    vc.record_mutation("pipe1", MutationType.UPDATE, {"a": 2})
    
    hist = vc.get_history("pipe1")
    assert len(hist) == 2
    assert hist[0].version_number == 2 # Reverse order

def test_diff_versions(temp_vc):
    vc, storage_dir = temp_vc
    
    vc.record_mutation("pipe1", MutationType.CREATE, {"a": 1, "b": 2})
    vc.record_mutation("pipe1", MutationType.UPDATE, {"a": 1, "b": 3, "c": 4})
    
    diff = vc.diff_versions("pipe1", 1, 2)
    assert diff["has_changes"] is True
    assert "c" in diff["changes"]["added"]
    assert diff["changes"]["modified"]["b"]["old"] == 2
    assert diff["changes"]["modified"]["b"]["new"] == 3

def test_rollback(temp_vc):
    vc, storage_dir = temp_vc
    
    vc.record_mutation("pipe1", MutationType.CREATE, {"a": 1})
    vc.record_mutation("pipe1", MutationType.UPDATE, {"a": 2})
    vc.record_mutation("pipe1", MutationType.UPDATE, {"a": 3})
    
    # Rollback to 1
    rb = vc.rollback("pipe1", 1, "admin")
    assert rb is not None
    assert rb.mutation_type == MutationType.ROLLBACK
    assert rb.version_number == 4
    assert rb.config_snapshot == {"a": 1}
    
    # Rollback nonexistent
    assert vc.rollback("pipe1", 100) is None

if __name__ == "__main__":
    pytest.main(['-v', __file__])
