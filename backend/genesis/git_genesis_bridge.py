import os
import subprocess
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
logger = logging.getLogger(__name__)

class GitGenesisBridge:
    """
    Bridge between Git and Genesis Keys.

    Provides bidirectional integration:
    1. Git commits → Genesis Keys (post-commit hook)
    2. Genesis Keys → Git commits (optional auto-commit)
    """

    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize Git-Genesis bridge.

        Args:
            repo_path: Path to Git repository (defaults to grace_3 root)
        """
        if repo_path is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            repo_path = os.path.dirname(backend_dir)

        self.repo_path = repo_path
        self.symbiotic_vc = None
        logger.info(f"GitGenesisBridge initialized for: {repo_path}")

    def _get_symbiotic_vc(self):
        """Lazy load symbiotic version control."""
        if self.symbiotic_vc is None:
            from genesis.symbiotic_version_control import get_symbiotic_version_control
            self.symbiotic_vc = get_symbiotic_version_control()
        return self.symbiotic_vc

    def _run_git_command(self, args: List[str]) -> Optional[str]:
        """
        Run a git command and return output.

        Args:
            args: Git command arguments (e.g., ['log', '-1', '--format=%H'])

        Returns:
            Command output or None if failed
        """
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Error running git command: {e}")
            return None

    def get_last_commit_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the last Git commit.

        Returns:
            Dictionary with commit info or None if failed
        """
        try:
            # Get commit SHA
            commit_sha = self._run_git_command(['log', '-1', '--format=%H'])
            if not commit_sha:
                return None

            # Get commit message
            commit_message = self._run_git_command(['log', '-1', '--format=%B'])

            # Get author
            author = self._run_git_command(['log', '-1', '--format=%an'])

            # Get author email
            author_email = self._run_git_command(['log', '-1', '--format=%ae'])

            # Get timestamp
            timestamp = self._run_git_command(['log', '-1', '--format=%ct'])

            return {
                "sha": commit_sha,
                "message": commit_message,
                "author": author,
                "author_email": author_email,
                "timestamp": int(timestamp) if timestamp else None,
                "timestamp_iso": datetime.fromtimestamp(int(timestamp)).isoformat() if timestamp else None
            }

        except Exception as e:
            logger.error(f"Error getting last commit info: {e}")
            return None

    def get_files_changed_in_last_commit(self) -> List[str]:
        """
        Get list of files changed in the last Git commit.

        Returns:
            List of file paths
        """
        try:
            output = self._run_git_command([
                'diff-tree',
                '--no-commit-id',
                '--name-only',
                '-r',
                'HEAD'
            ])

            if not output:
                return []

            files = [f.strip() for f in output.split('\n') if f.strip()]
            return files

        except Exception as e:
            logger.error(f"Error getting changed files: {e}")
            return []

    def sync_git_commit_to_genesis_keys(self, commit_sha: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync a Git commit to Genesis Keys.

        Creates Genesis Keys for all files changed in the commit.
        This is typically called from a post-commit hook.

        Args:
            commit_sha: Specific commit SHA (defaults to HEAD)

        Returns:
            Summary of Genesis Keys created
        """
        try:
            # Get commit info
            commit_info = self.get_last_commit_info()
            if not commit_info:
                return {
                    "status": "error",
                    "message": "Could not get commit info"
                }

            # Get changed files
            changed_files = self.get_files_changed_in_last_commit()
            if not changed_files:
                logger.info("No files changed in commit")
                return {
                    "status": "success",
                    "message": "No files to track",
                    "files_tracked": 0
                }

            # Track each changed file
            symbiotic = self._get_symbiotic_vc()
            genesis_keys_created = []
            errors = []

            for file_path in changed_files:
                try:
                    abs_path = os.path.join(self.repo_path, file_path)

                    # Only track if file still exists (not deleted)
                    if not os.path.exists(abs_path):
                        logger.debug(f"Skipping deleted file: {file_path}")
                        continue

                    # Create Genesis Key + Version
                    result = symbiotic.track_file_change(
                        file_path=file_path,
                        user_id=f"git:{commit_info['author_email']}",
                        change_description=f"Git commit: {commit_info['message'][:100]}",
                        operation_type="git_commit"
                    )

                    genesis_keys_created.append({
                        "file_path": file_path,
                        "genesis_key": result["operation_genesis_key"],
                        "version_number": result.get("version_number")
                    })

                    logger.info(
                        f"[GIT_GENESIS_BRIDGE] Tracked: {file_path} - "
                        f"Genesis Key: {result['operation_genesis_key']}"
                    )

                except Exception as file_error:
                    logger.error(f"Error tracking {file_path}: {file_error}")
                    errors.append({
                        "file_path": file_path,
                        "error": str(file_error)
                    })

            return {
                "status": "success",
                "commit_sha": commit_info["sha"],
                "commit_message": commit_info["message"],
                "commit_author": commit_info["author"],
                "files_tracked": len(genesis_keys_created),
                "genesis_keys": genesis_keys_created,
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error syncing Git commit to Genesis Keys: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    def create_post_commit_hook(self) -> bool:
        """
        Create Git post-commit hook that automatically creates Genesis Keys.

        This hook runs after every Git commit and creates Genesis Keys
        for all changed files.

        Returns:
            True if hook created successfully
        """
        try:
            hooks_dir = os.path.join(self.repo_path, '.git', 'hooks')
            hook_path = os.path.join(hooks_dir, 'post-commit')

            # Create hooks directory if it doesn't exist
            os.makedirs(hooks_dir, exist_ok=True)

            # Hook script content
            hook_content = '''#!/usr/bin/env python
"""
Git Post-Commit Hook - Genesis Keys Integration

Automatically creates Genesis Keys for all files changed in each commit.
This makes Git and Genesis Keys work as ONE unified version control system.
"""
import sys
import os

# Add backend to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend')
sys.path.insert(0, backend_dir)

try:
    from genesis.git_genesis_bridge import GitGenesisBridge

    # Sync this commit to Genesis Keys
    bridge = GitGenesisBridge()
    result = bridge.sync_git_commit_to_genesis_keys()

    if result.get("status") == "success":
        files_tracked = result.get("files_tracked", 0)
        if files_tracked > 0:
            print(f"[Genesis Keys] Tracked {files_tracked} files from Git commit")
    else:
        print(f"[Genesis Keys] Warning: {result.get('message', 'Unknown error')}")

except Exception as e:
    # Don't fail the commit if Genesis Keys tracking fails
    print(f"[Genesis Keys] Warning: Failed to track commit - {e}")
    pass
'''

            # Write hook file
            with open(hook_path, 'w', encoding='utf-8') as f:
                f.write(hook_content)

            # Make hook executable (on Unix systems)
            if os.name != 'nt':  # Not Windows
                os.chmod(hook_path, 0o755)

            logger.info(f"[GIT_GENESIS_BRIDGE] Created post-commit hook at: {hook_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating post-commit hook: {e}")
            return False

    def auto_commit_genesis_tracked_files(
        self,
        commit_message: str,
        file_paths: List[str]
    ) -> Optional[str]:
        """
        Automatically create a Git commit for Genesis-tracked files.

        This is the reverse direction: Genesis Keys → Git commits.
        When GRACE modifies files, it can optionally commit them to Git.

        Args:
            commit_message: Commit message
            file_paths: List of file paths to commit

        Returns:
            Commit SHA if successful, None otherwise
        """
        try:
            # Stage files
            for file_path in file_paths:
                self._run_git_command(['add', file_path])

            # Create commit
            self._run_git_command([
                'commit',
                '-m',
                f"{commit_message}\n\nCo-Authored-By: GRACE Autonomous System <grace@autonomous.ai>"
            ])

            # Get the new commit SHA
            commit_sha = self._run_git_command(['log', '-1', '--format=%H'])

            logger.info(f"[GIT_GENESIS_BRIDGE] Created Git commit: {commit_sha}")
            return commit_sha

        except Exception as e:
            logger.error(f"Error creating auto-commit: {e}")
            return None

    def get_bridge_statistics(self) -> Dict[str, Any]:
        """Get statistics about Git-Genesis bridge."""
        try:
            # Check if post-commit hook exists
            hook_path = os.path.join(self.repo_path, '.git', 'hooks', 'post-commit')
            hook_exists = os.path.exists(hook_path)

            # Get last commit info
            last_commit = self.get_last_commit_info()

            return {
                "repo_path": self.repo_path,
                "post_commit_hook_installed": hook_exists,
                "last_commit": last_commit,
                "status": "operational"
            }

        except Exception as e:
            logger.error(f"Error getting bridge statistics: {e}")
            return {
                "repo_path": self.repo_path,
                "error": str(e),
                "status": "error"
            }


# Global bridge instance
_git_genesis_bridge: Optional[GitGenesisBridge] = None


def get_git_genesis_bridge(repo_path: Optional[str] = None) -> GitGenesisBridge:
    """Get or create the global Git-Genesis bridge instance."""
    global _git_genesis_bridge
    if _git_genesis_bridge is None or repo_path is not None:
        _git_genesis_bridge = GitGenesisBridge(repo_path=repo_path)
    return _git_genesis_bridge
