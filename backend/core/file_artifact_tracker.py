import json
import hashlib
import os
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("file_artifact_tracker")

class FileArtifactTracker:
    """
    Produces the provenance baseline and handles drift detection.
    Matches the Guardian Boot Gate (Phase 1) requirements.
    """
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.baseline_path = self.root_dir / "provenance_baseline.json"
        
        # Avoid scanning common ignores
        self.ignore_dirs = {
            ".git", "__pycache__", "venv", "venv_gpu", ".pytest_cache", 
            ".genesis_snapshots", "logs", "cache", "mcp_repos", "__grACE_shadow"
        }
        self.ignore_extensions = {".pyc", ".log", ".bak", ".txt"}
        
    def _compute_file_hash(self, file_path: Path) -> str:
        """Computes SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def generate_baseline(self) -> Dict[str, Any]:
        """Generates the provenance baseline manifest."""
        manifest = {
            "version": "1.0",
            "files": {}
        }
        
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            # Prune ignored directories
            dirnames[:] = [d for d in dirnames if d not in self.ignore_dirs]
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix in self.ignore_extensions or filename == "provenance_baseline.json":
                    continue
                
                try:
                    rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
                    file_hash = self._compute_file_hash(file_path)
                    manifest["files"][rel_path] = {
                        "hash": file_hash,
                        "size": file_path.stat().st_size
                    }
                except Exception as e:
                    logger.warning(f"Could not hash {file_path}: {e}")

        with open(self.baseline_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
            
        logger.info(f"Generated provenance baseline with {len(manifest['files'])} files.")
        return manifest

    def detect_drift(self) -> List[Dict[str, Any]]:
        """
        Detects drift against the JSON baseline.
        Returns a list of drift artifacts (new, deleted, or modified files).
        """
        if not self.baseline_path.exists():
            raise FileNotFoundError("Baseline manifest not found. Cannot detect drift.")
            
        with open(self.baseline_path, "r", encoding="utf-8") as f:
            baseline = json.load(f)
            
        baseline_files = baseline.get("files", {})
        current_files = {}
        drifts = []
        
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            dirnames[:] = [d for d in dirnames if d not in self.ignore_dirs]
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix in self.ignore_extensions or filename == "provenance_baseline.json":
                    continue
                    
                rel_path = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
                current_files[rel_path] = file_path
                
        # Check for modified and new
        for rel_path, file_path in current_files.items():
            if rel_path not in baseline_files:
                drifts.append({"path": rel_path, "type": "new"})
            else:
                try:
                    current_hash = self._compute_file_hash(file_path)
                    if current_hash != baseline_files[rel_path]["hash"]:
                        drifts.append({"path": rel_path, "type": "modified", "expected": baseline_files[rel_path]["hash"], "actual": current_hash})
                except Exception as e:
                    logger.warning(f"Could not hash {file_path} for drift detection: {e}")
                    
        # Check for deleted
        for rel_path in baseline_files.keys():
            if rel_path not in current_files:
                drifts.append({"path": rel_path, "type": "deleted"})
                
        if drifts:
            logger.warning(f"Drift detected: {len(drifts)} anomalies found.")
        else:
            logger.info("No drift detected. Baseline integrity verified.")
            
        return drifts

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate new baseline")
    parser.add_argument("--detect", action="store_true", help="Detect drift")
    
    args = parser.parse_args()
    
    # Run from root dir
    root = Path(__file__).parent.parent.parent
    tracker = FileArtifactTracker(str(root))
    
    logging.basicConfig(level=logging.INFO)
    
    if args.generate:
        tracker.generate_baseline()
    elif args.detect:
        drifts = tracker.detect_drift()
        for drift in drifts:
            print(drift)
    else:
        print("Please specify --generate or --detect")
