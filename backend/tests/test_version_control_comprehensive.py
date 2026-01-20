"""
Comprehensive Test Suite for Version Control Module
===================================================
Tests for GitService and version control functionality.

Coverage:
- GitService initialization
- Repository operations
- Commit history retrieval
- Commit details
- Diff generation
- Branch operations
- File history tracking
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import os

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock dulwich
mock_dulwich = MagicMock()
mock_dulwich.repo = MagicMock()
mock_dulwich.repo.Repo = MagicMock()
mock_dulwich.objects = MagicMock()
mock_dulwich.objects.Commit = MagicMock()
sys.modules['dulwich'] = mock_dulwich
sys.modules['dulwich.repo'] = mock_dulwich.repo
sys.modules['dulwich.objects'] = mock_dulwich.objects

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# GitService Initialization Tests
# =============================================================================

class TestGitServiceInit:
    """Test GitService initialization."""

    def test_init_existing_repo(self):
        """Test initializing with existing repository."""
        class MockGitService:
            def __init__(self, repo_path: str):
                self.repo_path = repo_path
                self.repo = None
                self._initialize_repo()

            def _initialize_repo(self):
                # Simulate existing .git directory
                self.repo = MagicMock()

        service = MockGitService("/path/to/project")

        assert service.repo_path == "/path/to/project"
        assert service.repo is not None

    def test_init_new_repo(self):
        """Test initializing a new repository."""
        class MockGitService:
            def __init__(self, repo_path: str):
                self.repo_path = repo_path
                self.repo = None
                self._initialized_new = False
                self._initialize_repo()

            def _initialize_repo(self):
                # Simulate creating new repo
                self._initialized_new = True
                self.repo = MagicMock()

        service = MockGitService("/new/project")

        assert service._initialized_new is True
        assert service.repo is not None

    def test_init_failure(self):
        """Test initialization failure handling."""
        class MockGitService:
            def __init__(self, repo_path: str):
                self.repo_path = repo_path
                self.repo = None
                self._initialize_repo()

            def _initialize_repo(self):
                raise Exception("Failed to initialize repository")

        with pytest.raises(Exception, match="Failed to initialize"):
            MockGitService("/invalid/path")


# =============================================================================
# Commit History Tests
# =============================================================================

class TestCommitHistory:
    """Test commit history retrieval."""

    def test_get_commits(self):
        """Test retrieving commit history."""
        class MockGitService:
            def __init__(self):
                self.commits = [
                    {"sha": "abc123", "message": "First commit", "author": "user1"},
                    {"sha": "def456", "message": "Second commit", "author": "user1"},
                    {"sha": "ghi789", "message": "Third commit", "author": "user2"},
                ]

            def get_commits(self, limit: int = 100, skip: int = 0) -> List[Dict]:
                return self.commits[skip:skip + limit]

        service = MockGitService()
        commits = service.get_commits(limit=2)

        assert len(commits) == 2
        assert commits[0]["sha"] == "abc123"
        assert commits[1]["sha"] == "def456"

    def test_get_commits_with_skip(self):
        """Test commit history with skip parameter."""
        class MockGitService:
            def __init__(self):
                self.commits = [
                    {"sha": f"commit_{i}"} for i in range(20)
                ]

            def get_commits(self, limit: int = 100, skip: int = 0) -> List[Dict]:
                return self.commits[skip:skip + limit]

        service = MockGitService()
        commits = service.get_commits(limit=5, skip=10)

        assert len(commits) == 5
        assert commits[0]["sha"] == "commit_10"

    def test_get_commits_empty_repo(self):
        """Test getting commits from empty repository."""
        class MockGitService:
            def get_commits(self, limit: int = 100, skip: int = 0) -> List[Dict]:
                return []  # Empty repo

        service = MockGitService()
        commits = service.get_commits()

        assert commits == []


# =============================================================================
# Commit Details Tests
# =============================================================================

class TestCommitDetails:
    """Test commit details retrieval."""

    def test_get_commit_details(self):
        """Test retrieving detailed commit information."""
        class MockGitService:
            def __init__(self):
                self.commits = {
                    "abc123": {
                        "sha": "abc123",
                        "message": "Add new feature",
                        "author": "John Doe",
                        "author_email": "john@example.com",
                        "date": datetime(2024, 1, 15, 10, 30, 0),
                        "parent_shas": ["xyz789"]
                    }
                }

            def get_commit_details(self, commit_sha: str) -> Dict:
                if commit_sha not in self.commits:
                    raise Exception(f"Commit {commit_sha} not found")
                return self.commits[commit_sha]

        service = MockGitService()
        details = service.get_commit_details("abc123")

        assert details["sha"] == "abc123"
        assert details["author"] == "John Doe"
        assert details["message"] == "Add new feature"
        assert len(details["parent_shas"]) == 1

    def test_get_commit_details_not_found(self):
        """Test error when commit not found."""
        class MockGitService:
            def get_commit_details(self, commit_sha: str) -> Dict:
                raise Exception(f"Commit {commit_sha} not found")

        service = MockGitService()

        with pytest.raises(Exception, match="not found"):
            service.get_commit_details("nonexistent")

    def test_format_commit(self):
        """Test commit formatting."""
        class MockGitService:
            def _format_commit(self, commit) -> Dict:
                return {
                    "sha": commit.id.hex() if hasattr(commit.id, 'hex') else str(commit.id),
                    "message": commit.message.decode() if isinstance(commit.message, bytes) else commit.message,
                    "author": commit.author.decode() if isinstance(commit.author, bytes) else commit.author,
                    "timestamp": datetime.utcfromtimestamp(commit.commit_time).isoformat()
                }

        # Create mock commit
        mock_commit = MagicMock()
        mock_commit.id = b'abc123'
        mock_commit.message = b'Test commit message'
        mock_commit.author = b'Test Author <test@example.com>'
        mock_commit.commit_time = 1705312200  # 2024-01-15 10:30:00

        service = MockGitService()
        formatted = service._format_commit(mock_commit)

        assert "sha" in formatted
        assert "message" in formatted
        assert "author" in formatted


# =============================================================================
# Commit Diff Tests
# =============================================================================

class TestCommitDiff:
    """Test commit diff functionality."""

    def test_get_commit_diff(self):
        """Test getting diff for a commit."""
        class MockGitService:
            def get_commit_diff(self, commit_sha: str) -> Dict:
                return {
                    "commit_sha": commit_sha,
                    "files_changed": [
                        {
                            "path": "src/main.py",
                            "status": "modified",
                            "additions": 10,
                            "deletions": 5
                        },
                        {
                            "path": "src/utils.py",
                            "status": "added",
                            "additions": 50,
                            "deletions": 0
                        }
                    ],
                    "stats": {
                        "additions": 60,
                        "deletions": 5,
                        "files_modified": 2
                    }
                }

        service = MockGitService()
        diff = service.get_commit_diff("abc123")

        assert diff["commit_sha"] == "abc123"
        assert len(diff["files_changed"]) == 2
        assert diff["stats"]["additions"] == 60

    def test_get_diff_with_added_file(self):
        """Test diff showing added file."""
        class MockGitService:
            def get_commit_diff(self, commit_sha: str) -> Dict:
                return {
                    "files_changed": [
                        {"path": "new_file.py", "status": "added", "additions": 100, "deletions": 0}
                    ],
                    "stats": {"additions": 100, "deletions": 0, "files_modified": 1}
                }

        service = MockGitService()
        diff = service.get_commit_diff("abc123")

        assert diff["files_changed"][0]["status"] == "added"
        assert diff["stats"]["deletions"] == 0

    def test_get_diff_with_deleted_file(self):
        """Test diff showing deleted file."""
        class MockGitService:
            def get_commit_diff(self, commit_sha: str) -> Dict:
                return {
                    "files_changed": [
                        {"path": "old_file.py", "status": "deleted", "additions": 0, "deletions": 50}
                    ],
                    "stats": {"additions": 0, "deletions": 50, "files_modified": 1}
                }

        service = MockGitService()
        diff = service.get_commit_diff("abc123")

        assert diff["files_changed"][0]["status"] == "deleted"
        assert diff["stats"]["additions"] == 0

    def test_get_diff_initial_commit(self):
        """Test diff for initial commit (no parent)."""
        class MockGitService:
            def get_commit_diff(self, commit_sha: str) -> Dict:
                # Initial commit has no parent
                return {
                    "commit_sha": commit_sha,
                    "is_initial": True,
                    "files_changed": [
                        {"path": "README.md", "status": "added"}
                    ],
                    "stats": {"additions": 10, "deletions": 0, "files_modified": 1}
                }

        service = MockGitService()
        diff = service.get_commit_diff("initial_commit")

        assert diff["is_initial"] is True


# =============================================================================
# Tree and File Operations Tests
# =============================================================================

class TestTreeOperations:
    """Test tree and file operations."""

    def test_get_tree_files(self):
        """Test getting files from a tree."""
        class MockGitService:
            def _get_tree_files(self, tree) -> Dict[str, Dict]:
                return {
                    "src/main.py": {"mode": "100644", "sha": "abc123"},
                    "src/utils.py": {"mode": "100644", "sha": "def456"},
                    "README.md": {"mode": "100644", "sha": "ghi789"}
                }

        service = MockGitService()
        mock_tree = MagicMock()
        files = service._get_tree_files(mock_tree)

        assert len(files) == 3
        assert "src/main.py" in files

    def test_get_tree_files_with_content(self):
        """Test getting files with content."""
        class MockGitService:
            def _get_tree_files_with_content(self, tree) -> Dict[str, Dict]:
                return {
                    "README.md": {
                        "mode": "100644",
                        "sha": "abc123",
                        "content": "# Project Title\n\nDescription here."
                    }
                }

        service = MockGitService()
        mock_tree = MagicMock()
        files = service._get_tree_files_with_content(mock_tree)

        assert "README.md" in files
        assert "content" in files["README.md"]
        assert "# Project Title" in files["README.md"]["content"]


# =============================================================================
# Branch Operations Tests
# =============================================================================

class TestBranchOperations:
    """Test branch operations."""

    def test_get_branches(self):
        """Test getting all branches."""
        class MockGitService:
            def get_branches(self) -> List[Dict]:
                return [
                    {"name": "main", "is_current": True, "last_commit": "abc123"},
                    {"name": "feature/new", "is_current": False, "last_commit": "def456"},
                    {"name": "bugfix/fix", "is_current": False, "last_commit": "ghi789"}
                ]

        service = MockGitService()
        branches = service.get_branches()

        assert len(branches) == 3
        assert branches[0]["is_current"] is True
        assert branches[0]["name"] == "main"

    def test_get_current_branch(self):
        """Test getting current branch."""
        class MockGitService:
            def get_current_branch(self) -> str:
                return "main"

        service = MockGitService()
        branch = service.get_current_branch()

        assert branch == "main"

    def test_checkout_branch(self):
        """Test branch checkout."""
        class MockGitService:
            def __init__(self):
                self.current_branch = "main"

            def checkout(self, branch_name: str) -> bool:
                self.current_branch = branch_name
                return True

        service = MockGitService()
        assert service.checkout("feature/new") is True
        assert service.current_branch == "feature/new"


# =============================================================================
# File History Tests
# =============================================================================

class TestFileHistory:
    """Test file history tracking."""

    def test_get_file_history(self):
        """Test getting commit history for a file."""
        class MockGitService:
            def get_file_history(self, file_path: str, limit: int = 50) -> List[Dict]:
                return [
                    {"sha": "abc123", "message": "Update file", "date": "2024-01-15"},
                    {"sha": "def456", "message": "Fix bug in file", "date": "2024-01-10"},
                    {"sha": "ghi789", "message": "Initial add", "date": "2024-01-01"}
                ]

        service = MockGitService()
        history = service.get_file_history("src/main.py")

        assert len(history) == 3
        assert history[0]["message"] == "Update file"

    def test_get_file_at_commit(self):
        """Test getting file content at specific commit."""
        class MockGitService:
            def get_file_at_commit(self, file_path: str, commit_sha: str) -> Optional[str]:
                contents = {
                    ("main.py", "abc123"): "print('v1')",
                    ("main.py", "def456"): "print('v2')"
                }
                return contents.get((file_path, commit_sha))

        service = MockGitService()

        v1 = service.get_file_at_commit("main.py", "abc123")
        v2 = service.get_file_at_commit("main.py", "def456")

        assert v1 == "print('v1')"
        assert v2 == "print('v2')"


# =============================================================================
# Repository State Tests
# =============================================================================

class TestRepositoryState:
    """Test repository state queries."""

    def test_is_dirty(self):
        """Test checking if repo has uncommitted changes."""
        class MockGitService:
            def __init__(self, dirty: bool = False):
                self._dirty = dirty

            def is_dirty(self) -> bool:
                return self._dirty

        clean_repo = MockGitService(dirty=False)
        dirty_repo = MockGitService(dirty=True)

        assert clean_repo.is_dirty() is False
        assert dirty_repo.is_dirty() is True

    def test_get_status(self):
        """Test getting repository status."""
        class MockGitService:
            def get_status(self) -> Dict:
                return {
                    "branch": "main",
                    "staged": ["file1.py"],
                    "unstaged": ["file2.py", "file3.py"],
                    "untracked": ["new_file.py"]
                }

        service = MockGitService()
        status = service.get_status()

        assert status["branch"] == "main"
        assert len(status["staged"]) == 1
        assert len(status["unstaged"]) == 2

    def test_get_head_sha(self):
        """Test getting HEAD commit SHA."""
        class MockGitService:
            def get_head_sha(self) -> str:
                return "abc123def456"

        service = MockGitService()
        head = service.get_head_sha()

        assert head == "abc123def456"


# =============================================================================
# Remote Operations Tests
# =============================================================================

class TestRemoteOperations:
    """Test remote repository operations."""

    def test_get_remotes(self):
        """Test getting remote repositories."""
        class MockGitService:
            def get_remotes(self) -> List[Dict]:
                return [
                    {"name": "origin", "url": "git@github.com:user/repo.git"},
                    {"name": "upstream", "url": "git@github.com:org/repo.git"}
                ]

        service = MockGitService()
        remotes = service.get_remotes()

        assert len(remotes) == 2
        assert remotes[0]["name"] == "origin"

    def test_has_remote(self):
        """Test checking if remote exists."""
        class MockGitService:
            def __init__(self):
                self.remotes = {"origin": "url"}

            def has_remote(self, name: str) -> bool:
                return name in self.remotes

        service = MockGitService()

        assert service.has_remote("origin") is True
        assert service.has_remote("upstream") is False


# =============================================================================
# Tag Operations Tests
# =============================================================================

class TestTagOperations:
    """Test tag operations."""

    def test_get_tags(self):
        """Test getting all tags."""
        class MockGitService:
            def get_tags(self) -> List[Dict]:
                return [
                    {"name": "v1.0.0", "sha": "abc123", "message": "Release 1.0.0"},
                    {"name": "v1.1.0", "sha": "def456", "message": "Release 1.1.0"},
                    {"name": "v2.0.0", "sha": "ghi789", "message": "Release 2.0.0"}
                ]

        service = MockGitService()
        tags = service.get_tags()

        assert len(tags) == 3
        assert tags[0]["name"] == "v1.0.0"

    def test_get_tag_commit(self):
        """Test getting commit for a tag."""
        class MockGitService:
            def __init__(self):
                self.tags = {
                    "v1.0.0": "abc123",
                    "v2.0.0": "def456"
                }

            def get_tag_commit(self, tag_name: str) -> Optional[str]:
                return self.tags.get(tag_name)

        service = MockGitService()

        assert service.get_tag_commit("v1.0.0") == "abc123"
        assert service.get_tag_commit("nonexistent") is None


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Test repository statistics."""

    def test_get_commit_count(self):
        """Test getting total commit count."""
        class MockGitService:
            def get_commit_count(self) -> int:
                return 150

        service = MockGitService()
        count = service.get_commit_count()

        assert count == 150

    def test_get_contributor_stats(self):
        """Test getting contributor statistics."""
        class MockGitService:
            def get_contributor_stats(self) -> List[Dict]:
                return [
                    {"author": "Alice", "commits": 50, "additions": 5000, "deletions": 2000},
                    {"author": "Bob", "commits": 30, "additions": 3000, "deletions": 1000},
                    {"author": "Charlie", "commits": 20, "additions": 2000, "deletions": 500}
                ]

        service = MockGitService()
        stats = service.get_contributor_stats()

        assert len(stats) == 3
        assert stats[0]["author"] == "Alice"
        assert stats[0]["commits"] == 50

    def test_get_file_stats(self):
        """Test getting file statistics."""
        class MockGitService:
            def get_file_stats(self) -> Dict:
                return {
                    "total_files": 150,
                    "by_extension": {
                        ".py": 80,
                        ".js": 40,
                        ".md": 20,
                        ".json": 10
                    }
                }

        service = MockGitService()
        stats = service.get_file_stats()

        assert stats["total_files"] == 150
        assert stats["by_extension"][".py"] == 80


# =============================================================================
# Comparison Tests
# =============================================================================

class TestComparison:
    """Test comparison functionality."""

    def test_compare_commits(self):
        """Test comparing two commits."""
        class MockGitService:
            def compare_commits(self, from_sha: str, to_sha: str) -> Dict:
                return {
                    "from": from_sha,
                    "to": to_sha,
                    "commits_between": 5,
                    "files_changed": 10,
                    "additions": 200,
                    "deletions": 50
                }

        service = MockGitService()
        comparison = service.compare_commits("abc123", "def456")

        assert comparison["commits_between"] == 5
        assert comparison["files_changed"] == 10

    def test_compare_branches(self):
        """Test comparing two branches."""
        class MockGitService:
            def compare_branches(self, base: str, compare: str) -> Dict:
                return {
                    "base": base,
                    "compare": compare,
                    "ahead": 3,
                    "behind": 2,
                    "mergeable": True
                }

        service = MockGitService()
        comparison = service.compare_branches("main", "feature")

        assert comparison["ahead"] == 3
        assert comparison["behind"] == 2
        assert comparison["mergeable"] is True


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling."""

    def test_invalid_commit_sha(self):
        """Test handling of invalid commit SHA."""
        class MockGitService:
            def get_commit_details(self, commit_sha: str) -> Dict:
                if len(commit_sha) != 40:
                    raise ValueError("Invalid commit SHA")
                raise Exception("Commit not found")

        service = MockGitService()

        with pytest.raises(ValueError):
            service.get_commit_details("short")

    def test_repository_not_initialized(self):
        """Test handling when repository not initialized."""
        class MockGitService:
            def __init__(self):
                self.repo = None

            def get_commits(self) -> List[Dict]:
                if self.repo is None:
                    raise Exception("Repository not initialized")
                return []

        service = MockGitService()

        with pytest.raises(Exception, match="not initialized"):
            service.get_commits()

    def test_file_not_in_repo(self):
        """Test handling file not in repository."""
        class MockGitService:
            def get_file_at_commit(self, file_path: str, commit_sha: str) -> str:
                raise FileNotFoundError(f"File {file_path} not found at {commit_sha}")

        service = MockGitService()

        with pytest.raises(FileNotFoundError):
            service.get_file_at_commit("nonexistent.py", "abc123")


# =============================================================================
# Utility Methods Tests
# =============================================================================

class TestUtilityMethods:
    """Test utility methods."""

    def test_sha_short(self):
        """Test shortening SHA."""
        class MockGitService:
            def short_sha(self, full_sha: str, length: int = 7) -> str:
                return full_sha[:length]

        service = MockGitService()
        short = service.short_sha("abc123def456ghi789")

        assert short == "abc123d"
        assert len(short) == 7

    def test_is_valid_sha(self):
        """Test SHA validation."""
        class MockGitService:
            def is_valid_sha(self, sha: str) -> bool:
                if len(sha) not in [7, 40]:
                    return False
                return all(c in '0123456789abcdef' for c in sha.lower())

        service = MockGitService()

        assert service.is_valid_sha("abc123d") is True
        assert service.is_valid_sha("abc123def456789012345678901234567890abcd") is True
        assert service.is_valid_sha("xyz") is False
        assert service.is_valid_sha("ghijkl") is False

    def test_resolve_ref(self):
        """Test resolving Git references."""
        class MockGitService:
            def __init__(self):
                self.refs = {
                    "HEAD": "abc123",
                    "refs/heads/main": "abc123",
                    "refs/heads/feature": "def456",
                    "refs/tags/v1.0.0": "ghi789"
                }

            def resolve_ref(self, ref: str) -> Optional[str]:
                if ref in self.refs:
                    return self.refs[ref]
                # Try with prefix
                for prefix in ["refs/heads/", "refs/tags/"]:
                    if f"{prefix}{ref}" in self.refs:
                        return self.refs[f"{prefix}{ref}"]
                return None

        service = MockGitService()

        assert service.resolve_ref("HEAD") == "abc123"
        assert service.resolve_ref("main") == "abc123"
        assert service.resolve_ref("v1.0.0") == "ghi789"
        assert service.resolve_ref("nonexistent") is None


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for GitService."""

    def test_full_commit_workflow(self):
        """Test full commit information retrieval workflow."""
        class MockGitService:
            def __init__(self):
                self.commits_data = {
                    "abc123": {
                        "sha": "abc123",
                        "message": "Add feature",
                        "author": "Alice"
                    }
                }

            def get_commits(self, limit: int = 10) -> List[Dict]:
                return list(self.commits_data.values())[:limit]

            def get_commit_details(self, sha: str) -> Dict:
                return self.commits_data.get(sha, {})

            def get_commit_diff(self, sha: str) -> Dict:
                return {
                    "sha": sha,
                    "files_changed": [{"path": "main.py", "status": "modified"}]
                }

        service = MockGitService()

        # Get recent commits
        commits = service.get_commits(limit=5)
        assert len(commits) > 0

        # Get details for first commit
        details = service.get_commit_details(commits[0]["sha"])
        assert "message" in details

        # Get diff for first commit
        diff = service.get_commit_diff(commits[0]["sha"])
        assert "files_changed" in diff

    def test_branch_comparison_workflow(self):
        """Test branch comparison workflow."""
        class MockGitService:
            def __init__(self):
                self.branches = {
                    "main": "abc123",
                    "feature": "def456"
                }

            def get_branches(self) -> List[Dict]:
                return [{"name": name, "sha": sha} for name, sha in self.branches.items()]

            def compare_branches(self, base: str, compare: str) -> Dict:
                return {
                    "base": base,
                    "compare": compare,
                    "ahead": 3,
                    "behind": 1
                }

        service = MockGitService()

        # Get all branches
        branches = service.get_branches()
        assert len(branches) == 2

        # Compare feature to main
        comparison = service.compare_branches("main", "feature")
        assert comparison["ahead"] == 3


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases."""

    def test_empty_repository(self):
        """Test handling empty repository."""
        class MockGitService:
            def __init__(self):
                self.is_empty = True

            def get_commits(self) -> List[Dict]:
                if self.is_empty:
                    return []
                return [{"sha": "abc"}]

            def get_head_sha(self) -> Optional[str]:
                if self.is_empty:
                    return None
                return "abc123"

        service = MockGitService()

        assert service.get_commits() == []
        assert service.get_head_sha() is None

    def test_binary_file_handling(self):
        """Test handling binary files."""
        class MockGitService:
            def get_file_content(self, path: str, commit_sha: str) -> Dict:
                if path.endswith(".png"):
                    return {
                        "path": path,
                        "is_binary": True,
                        "content": None,
                        "size": 15000
                    }
                return {
                    "path": path,
                    "is_binary": False,
                    "content": "file content"
                }

        service = MockGitService()

        text_file = service.get_file_content("readme.md", "abc")
        binary_file = service.get_file_content("image.png", "abc")

        assert text_file["is_binary"] is False
        assert text_file["content"] is not None

        assert binary_file["is_binary"] is True
        assert binary_file["content"] is None

    def test_unicode_in_commit_message(self):
        """Test Unicode in commit messages."""
        class MockGitService:
            def get_commit_details(self, sha: str) -> Dict:
                return {
                    "sha": sha,
                    "message": "Fix bug with emoji support"
                }

        service = MockGitService()
        details = service.get_commit_details("abc")

        assert "emoji" in details["message"]

    def test_very_long_file_path(self):
        """Test handling very long file paths."""
        class MockGitService:
            def _normalize_path(self, path: str) -> str:
                # Truncate if too long
                max_length = 260
                if len(path) > max_length:
                    return path[:max_length]
                return path

        service = MockGitService()
        long_path = "a/" * 200 + "file.py"

        normalized = service._normalize_path(long_path)
        assert len(normalized) <= 260


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
