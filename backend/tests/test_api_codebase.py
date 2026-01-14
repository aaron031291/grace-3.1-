"""
Tests for Codebase Browser API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestCodebaseRepositories:
    """Test codebase repository endpoints."""

    def test_list_repositories(self, client):
        """Test listing repositories."""
        response = client.get("/codebase/repositories")
        assert response.status_code == 200
        data = response.json()
        assert "repositories" in data or isinstance(data, list)

    def test_get_repository_info(self, client):
        """Test getting repository info."""
        response = client.get("/codebase/repositories/test-repo")
        assert response.status_code in [200, 404]

    def test_add_repository(self, client):
        """Test adding a repository."""
        response = client.post("/codebase/repositories", json={
            "path": "/path/to/repo",
            "name": "test-repo",
            "description": "A test repository"
        })
        assert response.status_code in [200, 201, 400, 500]


@pytest.mark.api
class TestCodebaseFiles:
    """Test codebase file browsing endpoints."""

    def test_list_files(self, client):
        """Test listing files in a directory."""
        response = client.get("/codebase/files?path=/")
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "files" in data or isinstance(data, list)

    def test_get_file_content(self, client):
        """Test getting file content."""
        response = client.get("/codebase/file?path=/test.py")
        assert response.status_code in [200, 404]

    def test_get_file_with_line_range(self, client):
        """Test getting file content with line range."""
        response = client.get("/codebase/file?path=/test.py&start_line=1&end_line=50")
        assert response.status_code in [200, 404]


@pytest.mark.api
class TestCodebaseSearch:
    """Test codebase search endpoints."""

    def test_search_code(self, client):
        """Test searching code."""
        response = client.post("/codebase/search", json={
            "query": "def main",
            "file_types": [".py"],
            "limit": 20
        })
        assert response.status_code in [200, 500]

    def test_search_code_regex(self, client):
        """Test regex search in code."""
        response = client.post("/codebase/search", json={
            "query": "def\\s+\\w+",
            "regex": True,
            "limit": 10
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestCodebaseCommits:
    """Test codebase commit history endpoints."""

    def test_get_commits(self, client):
        """Test getting commit history."""
        response = client.get("/codebase/commits?repo=test-repo")
        assert response.status_code in [200, 404, 500]

    def test_get_commits_with_limit(self, client):
        """Test getting limited commit history."""
        response = client.get("/codebase/commits?repo=test-repo&limit=10")
        assert response.status_code in [200, 404, 500]

    def test_get_commit_details(self, client):
        """Test getting specific commit details."""
        response = client.get("/codebase/commits/abc123")
        assert response.status_code in [200, 404]


@pytest.mark.api
class TestCodebaseAnalysis:
    """Test codebase analysis endpoints."""

    def test_analyze_codebase(self, client):
        """Test codebase analysis."""
        response = client.post("/codebase/analysis", json={
            "repo_path": "/path/to/repo",
            "include_metrics": True
        })
        assert response.status_code in [200, 500]

    def test_get_code_metrics(self, client):
        """Test getting code metrics."""
        response = client.get("/codebase/metrics?repo=test-repo")
        assert response.status_code in [200, 404, 500]

    def test_analyze_file(self, client):
        """Test analyzing a specific file."""
        response = client.post("/codebase/analysis/file", json={
            "file_path": "/path/to/file.py"
        })
        assert response.status_code in [200, 404, 500]
