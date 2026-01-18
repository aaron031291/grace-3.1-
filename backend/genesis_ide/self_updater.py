import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import uuid
import shutil
logger = logging.getLogger(__name__)

class UpdateType:
    """Types of self-updates."""
    PATCH = "patch"           # Small fix
    ENHANCEMENT = "enhancement"  # Small improvement
    FEATURE = "feature"       # New capability
    REFACTOR = "refactor"     # Code improvement
    FIX = "fix"               # Bug fix
    EXPERIMENT = "experiment" # Experimental change


@dataclass
class SelfUpdate:
    """Record of a self-update."""
    update_id: str
    update_type: str
    description: str
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    genesis_key_id: Optional[str] = None
    commit_sha: Optional[str] = None
    status: str = "pending"  # pending, testing, verified, committed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "update_id": self.update_id,
            "update_type": self.update_type,
            "description": self.description,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "genesis_key_id": self.genesis_key_id,
            "commit_sha": self.commit_sha,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class SelfUpdater:
    """
    Self-update system for Grace.

    Enables Grace to:
    - Analyze her own codebase
    - Identify missing capabilities
    - Generate new code
    - Test the changes
    - Version control the update
    - Commit changes to herself
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None,
        genesis_service=None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()
        self._genesis_service = genesis_service

        # Update history
        self._updates: Dict[str, SelfUpdate] = {}

        # Safety constraints
        self.safety_config = {
            "require_tests": True,
            "min_test_coverage": 0.5,
            "require_backup": True,
            "max_files_per_update": 10,
            "protected_paths": [
                "genesis/",
                "config/",
                "__pycache__/"
            ]
        }

        # Metrics
        self.metrics = {
            "updates_attempted": 0,
            "updates_successful": 0,
            "updates_failed": 0,
            "total_files_created": 0,
            "total_files_modified": 0
        }

        logger.info("[SELF-UPDATER] Initialized")

    async def perform_update(
        self,
        update_type: str,
        description: str,
        target_files: List[str] = None,
        generated_code: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Perform a self-update.

        Args:
            update_type: Type of update
            description: What the update does
            target_files: Files to modify/create
            generated_code: Dict of file_path -> code content

        Returns:
            Update result
        """
        update = SelfUpdate(
            update_id=f"UPDATE-{uuid.uuid4().hex[:12]}",
            update_type=update_type,
            description=description
        )

        self._updates[update.update_id] = update
        self.metrics["updates_attempted"] += 1

        # Create genesis key for update
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.SELF_UPDATE,
                what_description=f"Self-update: {description[:100]}",
                who_actor="SelfUpdater",
                where_location=str(self.repo_path),
                why_reason=f"Self-improvement: {update_type}",
                how_method="Autonomous code generation",
                context_data={"update_id": update.update_id},
                session=self.session
            )
            update.genesis_key_id = genesis_key.key_id

        try:
            # Step 1: Create backup if required
            if self.safety_config["require_backup"]:
                await self._create_backup(update)

            # Step 2: Safety checks
            if target_files:
                safety_result = self._check_safety(target_files)
                if not safety_result["safe"]:
                    update.status = "failed"
                    update.error = safety_result["reason"]
                    return {"success": False, "error": safety_result["reason"]}

            # Step 3: Apply changes
            update.status = "applying"
            if generated_code:
                await self._apply_code_changes(update, generated_code)

            # Step 4: Run tests
            update.status = "testing"
            if self.safety_config["require_tests"]:
                test_result = await self._run_tests(update)
                update.tests_run = test_result["total"]
                update.tests_passed = test_result["passed"]

                if test_result["passed"] < test_result["total"] * self.safety_config["min_test_coverage"]:
                    update.status = "failed"
                    update.error = f"Insufficient test coverage: {test_result['passed']}/{test_result['total']}"
                    await self._rollback(update)
                    return {"success": False, "error": update.error}

            # Step 5: Verify the update
            update.status = "verified"

            # Step 6: Commit if all checks pass
            commit_result = await self._commit_update(update)
            if commit_result.get("success"):
                update.commit_sha = commit_result.get("sha")
                update.status = "committed"
                update.completed_at = datetime.utcnow()

                self.metrics["updates_successful"] += 1
                self.metrics["total_files_created"] += len(update.files_created)
                self.metrics["total_files_modified"] += len(update.files_modified)

                logger.info(f"[SELF-UPDATER] Update {update.update_id} committed successfully")

                return {
                    "success": True,
                    "update": update.to_dict()
                }
            else:
                update.status = "failed"
                update.error = commit_result.get("error")
                return {"success": False, "error": update.error}

        except Exception as e:
            update.status = "failed"
            update.error = str(e)
            self.metrics["updates_failed"] += 1

            logger.error(f"[SELF-UPDATER] Update {update.update_id} failed: {e}")

            # Rollback on error
            await self._rollback(update)

            return {"success": False, "error": str(e)}

    async def analyze_codebase(self) -> Dict[str, Any]:
        """
        Analyze Grace's own codebase to identify:
        - Missing capabilities
        - Incomplete implementations
        - Areas for improvement
        """
        analysis = {
            "total_files": 0,
            "total_lines": 0,
            "missing_capabilities": [],
            "incomplete_implementations": [],
            "improvement_opportunities": []
        }

        backend_path = self.repo_path / "backend"
        if not backend_path.exists():
            return {"error": "Backend not found"}

        try:
            # Count files and lines
            for py_file in backend_path.rglob("*.py"):
                analysis["total_files"] += 1
                try:
                    content = py_file.read_text()
                    analysis["total_lines"] += len(content.splitlines())

                    # Look for TODOs and NotImplemented
                    for i, line in enumerate(content.splitlines(), 1):
                        if "TODO" in line or "FIXME" in line:
                            analysis["incomplete_implementations"].append({
                                "file": str(py_file.relative_to(self.repo_path)),
                                "line": i,
                                "content": line.strip()[:100]
                            })
                        if "NotImplementedError" in line or "pass  #" in line:
                            analysis["missing_capabilities"].append({
                                "file": str(py_file.relative_to(self.repo_path)),
                                "line": i,
                                "content": line.strip()[:100]
                            })
                except Exception:
                    pass

            # Identify improvement opportunities
            if analysis["total_lines"] > 50000:
                analysis["improvement_opportunities"].append(
                    "Large codebase - consider modularization"
                )
            if len(analysis["incomplete_implementations"]) > 10:
                analysis["improvement_opportunities"].append(
                    f"{len(analysis['incomplete_implementations'])} TODOs/FIXMEs found"
                )
            if len(analysis["missing_capabilities"]) > 5:
                analysis["improvement_opportunities"].append(
                    f"{len(analysis['missing_capabilities'])} unimplemented features"
                )

        except Exception as e:
            analysis["error"] = str(e)

        return analysis

    async def suggest_update(self) -> Dict[str, Any]:
        """
        Suggest a self-update based on codebase analysis.
        """
        analysis = await self.analyze_codebase()

        if not analysis.get("missing_capabilities") and not analysis.get("incomplete_implementations"):
            return {
                "suggestion": None,
                "message": "No obvious improvements needed"
            }

        # Prioritize: NotImplemented > TODOs
        if analysis.get("missing_capabilities"):
            target = analysis["missing_capabilities"][0]
            return {
                "suggestion": {
                    "type": UpdateType.FEATURE,
                    "description": f"Implement missing capability in {target['file']}",
                    "target_file": target["file"],
                    "target_line": target["line"]
                },
                "priority": "high"
            }
        elif analysis.get("incomplete_implementations"):
            target = analysis["incomplete_implementations"][0]
            return {
                "suggestion": {
                    "type": UpdateType.FIX,
                    "description": f"Complete implementation in {target['file']}",
                    "target_file": target["file"],
                    "target_line": target["line"]
                },
                "priority": "medium"
            }

        return {"suggestion": None}

    def _check_safety(self, target_files: List[str]) -> Dict[str, Any]:
        """Check if the update is safe to apply."""
        # Check file count
        if len(target_files) > self.safety_config["max_files_per_update"]:
            return {
                "safe": False,
                "reason": f"Too many files: {len(target_files)} > {self.safety_config['max_files_per_update']}"
            }

        # Check protected paths
        for file_path in target_files:
            for protected in self.safety_config["protected_paths"]:
                if protected in file_path:
                    return {
                        "safe": False,
                        "reason": f"Cannot modify protected path: {protected}"
                    }

        return {"safe": True}

    async def _create_backup(self, update: SelfUpdate):
        """Create backup before making changes."""
        backup_dir = self.repo_path / ".grace" / "backups" / update.update_id
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Store update metadata
        with open(backup_dir / "update.json", "w") as f:
            json.dump(update.to_dict(), f, indent=2)

        logger.debug(f"[SELF-UPDATER] Backup created at {backup_dir}")

    async def _apply_code_changes(
        self,
        update: SelfUpdate,
        generated_code: Dict[str, str]
    ):
        """Apply generated code changes."""
        for file_path, code in generated_code.items():
            full_path = self.repo_path / file_path

            if full_path.exists():
                update.files_modified.append(file_path)
                # Backup original
                backup_path = self.repo_path / ".grace" / "backups" / update.update_id / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(full_path, backup_path)
            else:
                update.files_created.append(file_path)
                full_path.parent.mkdir(parents=True, exist_ok=True)

            full_path.write_text(code)

        logger.debug(f"[SELF-UPDATER] Applied {len(generated_code)} code changes")

    async def _run_tests(self, update: SelfUpdate) -> Dict[str, Any]:
        """Run tests to verify the update."""
        try:
            result = subprocess.run(
                ["pytest", "-v", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path / "backend")
            )

            # Parse test results
            output = result.stdout
            passed = output.count(" passed")
            failed = output.count(" failed")
            total = passed + failed if (passed + failed) > 0 else 1

            return {
                "success": result.returncode == 0,
                "total": total,
                "passed": passed,
                "failed": failed,
                "output": output[-2000:]  # Last 2000 chars
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "total": 0, "passed": 0, "error": "Test timeout"}
        except Exception as e:
            return {"success": False, "total": 0, "passed": 0, "error": str(e)}

    async def _rollback(self, update: SelfUpdate):
        """Rollback an update."""
        backup_dir = self.repo_path / ".grace" / "backups" / update.update_id

        if not backup_dir.exists():
            logger.warning(f"[SELF-UPDATER] No backup found for {update.update_id}")
            return

        # Restore modified files
        for file_path in update.files_modified:
            backup_path = backup_dir / file_path
            if backup_path.exists():
                full_path = self.repo_path / file_path
                shutil.copy(backup_path, full_path)

        # Remove created files
        for file_path in update.files_created:
            full_path = self.repo_path / file_path
            if full_path.exists():
                full_path.unlink()

        logger.info(f"[SELF-UPDATER] Rolled back update {update.update_id}")

    async def _commit_update(self, update: SelfUpdate) -> Dict[str, Any]:
        """Commit the update to version control."""
        try:
            # Stage files
            all_files = update.files_created + update.files_modified

            for file_path in all_files:
                subprocess.run(
                    ["git", "add", file_path],
                    cwd=str(self.repo_path),
                    check=True
                )

            # Commit
            commit_message = f"[Self-Update] {update.update_type}: {update.description[:50]}\n\n" \
                            f"Update ID: {update.update_id}\n" \
                            f"Genesis Key: {update.genesis_key_id}"

            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True,
                cwd=str(self.repo_path)
            )

            if result.returncode == 0:
                # Get commit SHA
                sha_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=str(self.repo_path)
                )
                return {
                    "success": True,
                    "sha": sha_result.stdout.strip()
                }
            else:
                return {"success": False, "error": result.stderr}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_update(self, update_id: str) -> Optional[Dict[str, Any]]:
        """Get an update record."""
        if update_id in self._updates:
            return self._updates[update_id].to_dict()
        return None

    def get_update_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent update history."""
        sorted_updates = sorted(
            self._updates.values(),
            key=lambda u: u.created_at,
            reverse=True
        )
        return [u.to_dict() for u in sorted_updates[:limit]]

    def get_metrics(self) -> Dict[str, Any]:
        """Get self-updater metrics."""
        return {
            **self.metrics,
            "pending_updates": sum(1 for u in self._updates.values() if u.status == "pending"),
            "recent_updates": len(self._updates)
        }
