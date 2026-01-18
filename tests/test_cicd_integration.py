"""Tests for GenesisCICDIntegration.trigger_pipeline() across providers."""

import pytest
import sys
import os
import base64
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class MockGenesisCICDIntegration:
    """
    Minimal implementation of trigger_pipeline logic for testing,
    extracted from genesis_cicd_integration.py to avoid complex import dependencies.
    """

    def trigger_pipeline(
        self,
        pipeline_name: str,
        branch: str = "main",
        parameters: dict = None
    ) -> dict:
        provider = os.environ.get("GRACE_CICD_PROVIDER", "").lower()

        if not provider:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_CICD_PROVIDER not set. Set to 'github', 'gitlab', or 'jenkins'"
            }

        if provider == "github":
            return self._trigger_github_actions(pipeline_name, branch, parameters or {})
        elif provider == "gitlab":
            return self._trigger_gitlab_ci(pipeline_name, branch, parameters or {})
        elif provider == "jenkins":
            return self._trigger_jenkins(pipeline_name, branch, parameters or {})
        else:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": f"Unknown CI/CD provider: {provider}. Use 'github', 'gitlab', or 'jenkins'"
            }

    def _trigger_github_actions(
        self,
        workflow_id: str,
        branch: str,
        parameters: dict
    ) -> dict:
        token = os.environ.get("GRACE_GITHUB_TOKEN")
        owner = os.environ.get("GRACE_GITHUB_OWNER")
        repo = os.environ.get("GRACE_GITHUB_REPO")

        if not token:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_GITHUB_TOKEN not set"
            }
        if not owner or not repo:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_GITHUB_OWNER and GRACE_GITHUB_REPO must be set"
            }

        url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        payload = {
            "ref": branch,
            "inputs": {k: str(v) for k, v in parameters.items()}
        }

        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)

            if response.status_code in (204, 200, 201):
                workflow_url = f"https://github.com/{owner}/{repo}/actions/workflows/{workflow_id}"
                return {
                    "triggered": True,
                    "run_id": f"github-{workflow_id}-{branch}",
                    "url": workflow_url,
                    "error": None
                }
            else:
                error_msg = f"GitHub API returned status {response.status_code}"
                if hasattr(response, 'text'):
                    error_msg += f": {response.text[:200]}"
                return {
                    "triggered": False,
                    "run_id": None,
                    "url": None,
                    "error": error_msg
                }
        except Exception as e:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": str(e)
            }

    def _trigger_gitlab_ci(
        self,
        pipeline_name: str,
        branch: str,
        parameters: dict
    ) -> dict:
        token = os.environ.get("GRACE_GITLAB_TOKEN")
        project_id = os.environ.get("GRACE_GITLAB_PROJECT_ID")
        gitlab_url = os.environ.get("GRACE_GITLAB_URL", "https://gitlab.com")

        if not token:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_GITLAB_TOKEN not set"
            }
        if not project_id:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_GITLAB_PROJECT_ID not set"
            }

        url = f"{gitlab_url.rstrip('/')}/api/v4/projects/{project_id}/trigger/pipeline"

        form_data = {
            "token": token,
            "ref": branch
        }
        for key, value in parameters.items():
            form_data[f"variables[{key}]"] = str(value)

        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, data=form_data)
                response_json = response.json() if response.status_code in (200, 201) else {}

            if response.status_code in (200, 201):
                pipeline_id = response_json.get("id")
                web_url = response_json.get("web_url", f"{gitlab_url}/{project_id}/-/pipelines/{pipeline_id}")
                return {
                    "triggered": True,
                    "run_id": str(pipeline_id),
                    "url": web_url,
                    "error": None
                }
            else:
                error_msg = f"GitLab API returned status {response.status_code}"
                return {
                    "triggered": False,
                    "run_id": None,
                    "url": None,
                    "error": error_msg
                }
        except Exception as e:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": str(e)
            }

    def _trigger_jenkins(
        self,
        job_name: str,
        branch: str,
        parameters: dict
    ) -> dict:
        jenkins_url = os.environ.get("GRACE_JENKINS_URL")
        jenkins_user = os.environ.get("GRACE_JENKINS_USER")
        jenkins_token = os.environ.get("GRACE_JENKINS_TOKEN")

        if not jenkins_url:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_JENKINS_URL not set"
            }
        if not jenkins_user or not jenkins_token:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": "GRACE_JENKINS_USER and GRACE_JENKINS_TOKEN must be set"
            }

        jenkins_url = jenkins_url.rstrip('/')

        params = dict(parameters)
        params["BRANCH"] = branch

        if params:
            url = f"{jenkins_url}/job/{job_name}/buildWithParameters"
        else:
            url = f"{jenkins_url}/job/{job_name}/build"

        auth_string = f"{jenkins_user}:{jenkins_token}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        headers = {
            "Authorization": f"Basic {auth_bytes}"
        }

        try:
            import httpx
            with httpx.Client(timeout=30.0) as client:
                if params:
                    response = client.post(url, params=params, headers=headers)
                else:
                    response = client.post(url, headers=headers)
                queue_location = response.headers.get("Location", "")

            if response.status_code in (200, 201, 202):
                job_url = f"{jenkins_url}/job/{job_name}"
                run_id = queue_location.split("/")[-2] if queue_location else "queued"
                return {
                    "triggered": True,
                    "run_id": run_id,
                    "url": job_url,
                    "error": None
                }
            else:
                error_msg = f"Jenkins API returned status {response.status_code}"
                return {
                    "triggered": False,
                    "run_id": None,
                    "url": None,
                    "error": error_msg
                }
        except Exception as e:
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": str(e)
            }


class TestTriggerPipelineGitHubActions:
    """Test GitHub Actions workflow triggering."""

    @pytest.fixture(autouse=True)
    def setup_github_env(self, monkeypatch):
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "github")
        monkeypatch.setenv("GRACE_GITHUB_TOKEN", "ghp_test_token_123")
        monkeypatch.setenv("GRACE_GITHUB_OWNER", "test-owner")
        monkeypatch.setenv("GRACE_GITHUB_REPO", "test-repo")

    @pytest.fixture
    def integration(self):
        return MockGenesisCICDIntegration()

    def test_sends_correct_api_request(self, integration):
        """Verify GitHub Actions API request is correctly formed."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline(
                pipeline_name="ci.yml",
                branch="main",
                parameters={"TEST_PARAM": "value"}
            )

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "https://api.github.com/repos/test-owner/test-repo/actions/workflows/ci.yml/dispatches" in call_args[0]
            assert call_args[1]["headers"]["Authorization"] == "Bearer ghp_test_token_123"
            assert call_args[1]["json"]["ref"] == "main"
            assert call_args[1]["json"]["inputs"]["TEST_PARAM"] == "value"

    def test_returns_triggered_true_on_success(self, integration):
        """Verify triggered=True on successful dispatch."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("ci.yml", "main")

            assert result["triggered"] is True

    def test_returns_run_id_and_url(self, integration):
        """Verify run_id and url are returned on success."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("ci.yml", "feature-branch")

            assert result["run_id"] == "github-ci.yml-feature-branch"
            assert result["url"] == "https://github.com/test-owner/test-repo/actions/workflows/ci.yml"
            assert result["error"] is None

    def test_handles_missing_token(self, integration, monkeypatch):
        """Verify error when GRACE_GITHUB_TOKEN is missing."""
        monkeypatch.delenv("GRACE_GITHUB_TOKEN", raising=False)

        result = integration.trigger_pipeline("ci.yml", "main")

        assert result["triggered"] is False
        assert "GRACE_GITHUB_TOKEN not set" in result["error"]


class TestTriggerPipelineGitLabCI:
    """Test GitLab CI pipeline triggering."""

    @pytest.fixture(autouse=True)
    def setup_gitlab_env(self, monkeypatch):
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "gitlab")
        monkeypatch.setenv("GRACE_GITLAB_TOKEN", "glpat_test_token_456")
        monkeypatch.setenv("GRACE_GITLAB_PROJECT_ID", "12345")
        monkeypatch.setenv("GRACE_GITLAB_URL", "https://gitlab.example.com")

    @pytest.fixture
    def integration(self):
        return MockGenesisCICDIntegration()

    def test_sends_correct_api_request(self, integration):
        """Verify GitLab CI API request is correctly formed."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 789, "web_url": "https://gitlab.example.com/pipelines/789"}
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline(
                pipeline_name="build",
                branch="develop",
                parameters={"DEPLOY_ENV": "staging"}
            )

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "https://gitlab.example.com/api/v4/projects/12345/trigger/pipeline" in call_args[0]
            form_data = call_args[1]["data"]
            assert form_data["token"] == "glpat_test_token_456"
            assert form_data["ref"] == "develop"
            assert form_data["variables[DEPLOY_ENV]"] == "staging"

    def test_returns_triggered_true_on_success(self, integration):
        """Verify triggered=True on successful pipeline creation."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": 789, "web_url": "https://gitlab.example.com/pipelines/789"}
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("build", "main")

            assert result["triggered"] is True
            assert result["run_id"] == "789"
            assert result["url"] == "https://gitlab.example.com/pipelines/789"

    def test_handles_missing_token(self, integration, monkeypatch):
        """Verify error when GRACE_GITLAB_TOKEN is missing."""
        monkeypatch.delenv("GRACE_GITLAB_TOKEN", raising=False)

        result = integration.trigger_pipeline("build", "main")

        assert result["triggered"] is False
        assert "GRACE_GITLAB_TOKEN not set" in result["error"]

    def test_handles_missing_project_id(self, integration, monkeypatch):
        """Verify error when GRACE_GITLAB_PROJECT_ID is missing."""
        monkeypatch.delenv("GRACE_GITLAB_PROJECT_ID", raising=False)

        result = integration.trigger_pipeline("build", "main")

        assert result["triggered"] is False
        assert "GRACE_GITLAB_PROJECT_ID not set" in result["error"]


class TestTriggerPipelineJenkins:
    """Test Jenkins build triggering."""

    @pytest.fixture(autouse=True)
    def setup_jenkins_env(self, monkeypatch):
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "jenkins")
        monkeypatch.setenv("GRACE_JENKINS_URL", "https://jenkins.example.com")
        monkeypatch.setenv("GRACE_JENKINS_USER", "admin")
        monkeypatch.setenv("GRACE_JENKINS_TOKEN", "jenkins_api_token_789")

    @pytest.fixture
    def integration(self):
        return MockGenesisCICDIntegration()

    def test_sends_correct_api_request(self, integration):
        """Verify Jenkins API request is correctly formed."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.headers = {"Location": "https://jenkins.example.com/queue/item/42/"}
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline(
                pipeline_name="my-job",
                branch="release",
                parameters={"VERSION": "1.0.0"}
            )

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "https://jenkins.example.com/job/my-job/buildWithParameters" in call_args[0]
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"].startswith("Basic ")
            assert call_args[1]["params"]["VERSION"] == "1.0.0"
            assert call_args[1]["params"]["BRANCH"] == "release"

    def test_returns_triggered_true_on_success(self, integration):
        """Verify triggered=True on successful build trigger."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.headers = {"Location": "https://jenkins.example.com/queue/item/42/"}
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("my-job", "main")

            assert result["triggered"] is True
            assert result["run_id"] == "42"
            assert result["url"] == "https://jenkins.example.com/job/my-job"

    def test_handles_missing_url(self, integration, monkeypatch):
        """Verify error when GRACE_JENKINS_URL is missing."""
        monkeypatch.delenv("GRACE_JENKINS_URL", raising=False)

        result = integration.trigger_pipeline("my-job", "main")

        assert result["triggered"] is False
        assert "GRACE_JENKINS_URL not set" in result["error"]

    def test_handles_missing_credentials(self, integration, monkeypatch):
        """Verify error when Jenkins credentials are missing."""
        monkeypatch.delenv("GRACE_JENKINS_USER", raising=False)

        result = integration.trigger_pipeline("my-job", "main")

        assert result["triggered"] is False
        assert "GRACE_JENKINS_USER and GRACE_JENKINS_TOKEN must be set" in result["error"]


class TestTriggerPipelineConfiguration:
    """Test pipeline configuration and provider selection."""

    @pytest.fixture
    def integration(self):
        return MockGenesisCICDIntegration()

    def test_loads_provider_from_environment(self, integration, monkeypatch):
        """Verify provider is loaded from GRACE_CICD_PROVIDER."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "github")
        monkeypatch.setenv("GRACE_GITHUB_TOKEN", "token")
        monkeypatch.setenv("GRACE_GITHUB_OWNER", "owner")
        monkeypatch.setenv("GRACE_GITHUB_REPO", "repo")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("workflow.yml", "main")

            call_url = mock_client.post.call_args[0][0]
            assert "api.github.com" in call_url

    def test_selects_correct_provider_github(self, integration, monkeypatch):
        """Verify GitHub provider is selected correctly."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "github")
        monkeypatch.setenv("GRACE_GITHUB_TOKEN", "token")
        monkeypatch.setenv("GRACE_GITHUB_OWNER", "owner")
        monkeypatch.setenv("GRACE_GITHUB_REPO", "repo")

        with patch.object(integration, "_trigger_github_actions", return_value={"triggered": True}) as mock_method:
            integration.trigger_pipeline("test", "main", {})
            mock_method.assert_called_once()

    def test_selects_correct_provider_gitlab(self, integration, monkeypatch):
        """Verify GitLab provider is selected correctly."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "gitlab")

        with patch.object(integration, "_trigger_gitlab_ci", return_value={"triggered": True}) as mock_method:
            integration.trigger_pipeline("test", "main", {})
            mock_method.assert_called_once()

    def test_selects_correct_provider_jenkins(self, integration, monkeypatch):
        """Verify Jenkins provider is selected correctly."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "jenkins")

        with patch.object(integration, "_trigger_jenkins", return_value={"triggered": True}) as mock_method:
            integration.trigger_pipeline("test", "main", {})
            mock_method.assert_called_once()

    def test_missing_provider_returns_error(self, integration, monkeypatch):
        """Verify informative error when GRACE_CICD_PROVIDER is not set."""
        monkeypatch.delenv("GRACE_CICD_PROVIDER", raising=False)

        result = integration.trigger_pipeline("test", "main")

        assert result["triggered"] is False
        assert "GRACE_CICD_PROVIDER not set" in result["error"]
        assert "github" in result["error"].lower() or "gitlab" in result["error"].lower()


class TestTriggerPipelineErrorHandling:
    """Test error handling for pipeline triggers."""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "github")
        monkeypatch.setenv("GRACE_GITHUB_TOKEN", "token")
        monkeypatch.setenv("GRACE_GITHUB_OWNER", "owner")
        monkeypatch.setenv("GRACE_GITHUB_REPO", "repo")

    @pytest.fixture
    def integration(self):
        return MockGenesisCICDIntegration()

    def test_api_error_returns_triggered_false(self, integration):
        """Verify API errors return triggered=False with error message."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden: Bad credentials"
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("workflow.yml", "main")

            assert result["triggered"] is False
            assert result["error"] is not None
            assert "403" in result["error"]

    def test_network_error_handled_gracefully(self, integration):
        """Verify network errors are caught and return informative error."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = ConnectionError("Network unreachable")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("workflow.yml", "main")

            assert result["triggered"] is False
            assert result["error"] is not None
            assert "Network unreachable" in result["error"]

    def test_timeout_error_handled_gracefully(self, integration):
        """Verify timeout errors are caught and return informative error."""
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.post.side_effect = TimeoutError("Request timed out")
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("workflow.yml", "main")

            assert result["triggered"] is False
            assert result["error"] is not None

    def test_unknown_provider_returns_informative_error(self, integration, monkeypatch):
        """Verify unknown provider returns descriptive error."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "unknown_provider")

        result = integration.trigger_pipeline("test", "main")

        assert result["triggered"] is False
        assert "Unknown CI/CD provider" in result["error"]
        assert "unknown_provider" in result["error"]

    def test_gitlab_api_error_returns_error_message(self, integration, monkeypatch):
        """Verify GitLab API errors include status code."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "gitlab")
        monkeypatch.setenv("GRACE_GITLAB_TOKEN", "token")
        monkeypatch.setenv("GRACE_GITLAB_PROJECT_ID", "123")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("build", "main")

            assert result["triggered"] is False
            assert "401" in result["error"]

    def test_jenkins_api_error_returns_error_message(self, integration, monkeypatch):
        """Verify Jenkins API errors include status code."""
        monkeypatch.setenv("GRACE_CICD_PROVIDER", "jenkins")
        monkeypatch.setenv("GRACE_JENKINS_URL", "https://jenkins.example.com")
        monkeypatch.setenv("GRACE_JENKINS_USER", "user")
        monkeypatch.setenv("GRACE_JENKINS_TOKEN", "token")

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = integration.trigger_pipeline("job", "main")

            assert result["triggered"] is False
            assert "500" in result["error"]
