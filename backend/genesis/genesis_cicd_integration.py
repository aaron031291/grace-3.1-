import logging
import os
import base64
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from models.genesis_key_models import GenesisKey, GenesisKeyType
from genesis.intelligent_cicd_orchestrator import IntelligentTestSelector, TestSelectionStrategy, IntelligenceMode
from genesis.code_change_analyzer import ChangeAnalysis
from genesis.cicd import GenesisCICD, get_cicd
from genesis.predictive_failure_detector import get_predictive_failure_detector
from genesis.autonomous_code_reviewer import get_autonomous_code_reviewer
from genesis.proactive_test_generator import get_proactive_test_generator
from genesis.semantic_intent_analyzer import get_semantic_intent_analyzer

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
class GenesisCICDIntegration:
    logger = logging.getLogger(__name__)
    """
    Integrates Genesis Keys with CI/CD for intelligent, autonomous testing.
    
    This is the "Grace Way" - goes beyond traditional Git by:
    - Understanding code semantics (not just file diffs)
    - Selecting only affected tests (10x faster)
    - Learning from outcomes (gets smarter over time)
    - Autonomous healing (fixes issues automatically)
    """

    def __init__(
        self,
        session: Session,
        base_path: Optional[str] = None
    ):
        self.session = session
        self.base_path = base_path
        self.test_selector = IntelligentTestSelector(base_path=base_path)
        self.cicd = get_cicd()
        self.failure_detector = get_predictive_failure_detector()
        self.code_reviewer = get_autonomous_code_reviewer()
        self.test_generator = get_proactive_test_generator()
        self.intent_analyzer = get_semantic_intent_analyzer()
        self.integrations_count = 0

    def on_code_change_genesis_key(
        self,
        genesis_key: GenesisKey
    ) -> Dict[str, Any]:
        """
        Handle a CODE_CHANGE Genesis Key by triggering intelligent CI/CD.
        
        This is called automatically when a code change Genesis Key is created.
        
        Args:
            genesis_key: Genesis Key representing the code change
            
        Returns:
            Dict with CI/CD trigger results and test selection
        """
        if genesis_key.key_type not in [
            GenesisKeyType.CODE_CHANGE,
            GenesisKeyType.FILE_OPERATION
        ]:
            return {
                "triggered": False,
                "reason": f"Genesis Key type {genesis_key.key_type} is not a code change"
            }

        logger.info(
            f"[GenesisCICD] Processing code change Genesis Key: {genesis_key.key_id}"
        )

        try:
            # 1. Analyze the code change semantically
            selected_tests, change_analysis = self.test_selector.select_tests_from_genesis_key(
                genesis_key=genesis_key,
                strategy=TestSelectionStrategy.IMPACT_ANALYSIS
            )

            if not change_analysis:
                logger.warning(
                    f"[GenesisCICD] Could not analyze Genesis Key {genesis_key.key_id}"
                )
                return {
                    "triggered": False,
                    "reason": "Could not analyze code change"
                }

            # 2. Advanced Analysis (BEYOND traditional CI/CD)
            # 2a. Predict failures BEFORE running tests
            failure_predictions = self.failure_detector.predict_failures(
                genesis_key=genesis_key,
                change_analysis=change_analysis,
                test_ids=selected_tests
            )
            
            # 2b. Autonomous code review
            code_review = self.code_reviewer.review_code_change(
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            
            # 2c. Understand intent
            intent_analysis = self.intent_analyzer.analyze_intent(
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            
            # 2d. Generate tests proactively
            test_generation_plan = self.test_generator.generate_tests_for_change(
                genesis_key=genesis_key,
                change_analysis=change_analysis
            )
            
            # 3. Build intelligent CI/CD pipeline configuration
            pipeline_config = self._build_intelligent_pipeline_config(
                genesis_key=genesis_key,
                change_analysis=change_analysis,
                selected_tests=selected_tests,
                failure_predictions=failure_predictions,
                code_review=code_review,
                intent_analysis=intent_analysis,
                test_generation=test_generation_plan
            )

            # 3. Trigger CI/CD pipeline with intelligent test selection
            pipeline_run = self._trigger_intelligent_pipeline(
                genesis_key=genesis_key,
                pipeline_config=pipeline_config
            )

            self.integrations_count += 1

            return {
                "triggered": True,
                "genesis_key_id": genesis_key.key_id,
                "pipeline_run_id": pipeline_run.id if pipeline_run else None,
                "tests_selected": len(selected_tests),
                "test_ids": selected_tests,
                "change_analysis": {
                    "risk_score": change_analysis.risk_score,
                    "confidence": change_analysis.confidence,
                    "affected_files": change_analysis.affected_files,
                    "affected_functions": change_analysis.affected_functions,
                    "estimated_test_time": change_analysis.estimated_test_time
                },
                "pipeline_config": pipeline_config
            }

        except Exception as e:
            logger.error(f"[GenesisCICD] Error processing Genesis Key {genesis_key.key_id}: {e}")
            return {
                "triggered": False,
                "error": str(e)
            }

    def _build_intelligent_pipeline_config(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis,
        selected_tests: List[str],
        failure_predictions: List = None,
        code_review = None,
        intent_analysis = None,
        test_generation = None
    ) -> Dict[str, Any]:
        """Build intelligent CI/CD pipeline configuration from analysis."""
        config = {
            "genesis_key_id": genesis_key.key_id,
            "file_path": genesis_key.file_path,
            "risk_score": change_analysis.risk_score,
            "confidence": change_analysis.confidence,
            "selected_tests": selected_tests,
            "test_count": len(selected_tests),
            "estimated_time": change_analysis.estimated_test_time,
            "affected_files": change_analysis.affected_files,
            "affected_functions": change_analysis.affected_functions,
            "strategy": "intelligent_selection",
            "intelligence_mode": IntelligenceMode.ML_ASSISTED.value,
            # Advanced features
            "failure_predictions": [
                {
                    "test_id": p.test_id,
                    "failure_probability": p.failure_probability,
                    "predicted_type": p.predicted_failure_type
                }
                for p in (failure_predictions or [])[:5]  # Top 5 predictions
            ],
            "code_review": {
                "score": code_review.overall_score if code_review else 1.0,
                "issues_count": len(code_review.issues) if code_review else 0,
                "critical_issues": len([
                    i for i in (code_review.issues or [])
                    if i.severity.value in ['error', 'critical']
                ]) if code_review else 0
            },
            "intent": {
                "primary": intent_analysis.primary_intent.value if intent_analysis else "unknown",
                "confidence": intent_analysis.confidence if intent_analysis else 0.0,
                "suggested_followups": intent_analysis.suggested_followups if intent_analysis else []
            },
            "generated_tests": {
                "count": len(test_generation.generated_tests) if test_generation else 0,
                "coverage_estimate": test_generation.coverage_estimate if test_generation else 0.0
            }
        }

        # Adjust pipeline behavior based on risk
        if change_analysis.risk_score > 0.7:
            config["run_full_suite"] = True  # High risk - run more tests
            config["security_scan"] = True
            config["code_review_required"] = True
        elif change_analysis.risk_score > 0.4:
            config["run_full_suite"] = False
            config["security_scan"] = True
            config["code_review_required"] = False
        else:
            config["run_full_suite"] = False
            config["security_scan"] = False
            config["code_review_required"] = False

        return config

    def _trigger_intelligent_pipeline(
        self,
        genesis_key: GenesisKey,
        pipeline_config: Dict[str, Any]
    ):
        """Trigger CI/CD pipeline with intelligent configuration."""
        try:
            logger.info(
                f"[GenesisCICD] Triggering pipeline for {genesis_key.key_id} "
                f"with {pipeline_config['test_count']} tests "
                f"(risk={pipeline_config['risk_score']:.2f})"
            )
            
            result = self.trigger_pipeline(
                pipeline_name="grace-ci-intelligent",
                branch="main",
                parameters={
                    "GENESIS_KEY_ID": genesis_key.key_id,
                    "SELECTED_TESTS": ",".join(pipeline_config['selected_tests']),
                    "RISK_SCORE": str(pipeline_config['risk_score']),
                    "ESTIMATED_TIME": str(pipeline_config['estimated_time'])
                }
            )
            
            if result.get("triggered"):
                class PipelineRun:
                    def __init__(self, run_id):
                        self.id = run_id
                return PipelineRun(result.get("run_id"))
            
            return None
            
        except Exception as e:
            logger.error(f"[GenesisCICD] Error triggering pipeline: {e}")
            return None

    def trigger_pipeline(
        self,
        pipeline_name: str,
        branch: str = "main",
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Trigger a CI/CD pipeline across multiple providers.
        
        Supports:
        - GitHub Actions (via workflow_dispatch)
        - GitLab CI (via pipeline triggers)
        - Jenkins (via build triggers)
        
        Configuration via environment variables:
        - GRACE_CICD_PROVIDER: 'github', 'gitlab', or 'jenkins'
        - GRACE_GITHUB_TOKEN: GitHub personal access token
        - GRACE_GITHUB_OWNER: GitHub repository owner
        - GRACE_GITHUB_REPO: GitHub repository name
        - GRACE_GITLAB_TOKEN: GitLab personal access token
        - GRACE_GITLAB_PROJECT_ID: GitLab project ID
        - GRACE_GITLAB_URL: GitLab instance URL (default: https://gitlab.com)
        - GRACE_JENKINS_URL: Jenkins server URL
        - GRACE_JENKINS_USER: Jenkins username
        - GRACE_JENKINS_TOKEN: Jenkins API token
        
        Args:
            pipeline_name: Name/ID of the pipeline/workflow to trigger
            branch: Branch to run the pipeline on (default: main)
            parameters: Additional parameters to pass to the pipeline
            
        Returns:
            Dict with keys: triggered, run_id, url, error
        """
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
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow using workflow_dispatch."""
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
            if HTTPX_AVAILABLE:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, json=payload, headers=headers)
            else:
                import urllib.request
                import json
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    response_code = resp.getcode()
                    class MockResponse:
                        def __init__(self, code):
                            self.status_code = code
                    response = MockResponse(response_code)
            
            if response.status_code in (204, 200, 201):
                workflow_url = f"https://github.com/{owner}/{repo}/actions/workflows/{workflow_id}"
                logger.info(f"[GenesisCICD] GitHub Actions workflow triggered: {workflow_id}")
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
            logger.error(f"[GenesisCICD] GitHub Actions trigger failed: {e}")
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
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger a GitLab CI pipeline using pipeline triggers."""
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
            if HTTPX_AVAILABLE:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, data=form_data)
                    response_json = response.json() if response.status_code in (200, 201) else {}
            else:
                import urllib.request
                import urllib.parse
                import json
                encoded_data = urllib.parse.urlencode(form_data).encode('utf-8')
                req = urllib.request.Request(url, data=encoded_data, method='POST')
                with urllib.request.urlopen(req, timeout=30) as resp:
                    response_code = resp.getcode()
                    response_json = json.loads(resp.read().decode('utf-8')) if response_code in (200, 201) else {}
                    class MockResponse:
                        def __init__(self, code):
                            self.status_code = code
                    response = MockResponse(response_code)
            
            if response.status_code in (200, 201):
                pipeline_id = response_json.get("id")
                web_url = response_json.get("web_url", f"{gitlab_url}/{project_id}/-/pipelines/{pipeline_id}")
                logger.info(f"[GenesisCICD] GitLab CI pipeline triggered: {pipeline_id}")
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
            logger.error(f"[GenesisCICD] GitLab CI trigger failed: {e}")
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
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger a Jenkins build using build triggers."""
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
            if HTTPX_AVAILABLE:
                with httpx.Client(timeout=30.0) as client:
                    if params:
                        response = client.post(url, params=params, headers=headers)
                    else:
                        response = client.post(url, headers=headers)
                    queue_location = response.headers.get("Location", "")
            else:
                import urllib.request
                import urllib.parse
                if params:
                    url = f"{url}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers=headers, method='POST')
                req.data = b''
                with urllib.request.urlopen(req, timeout=30) as resp:
                    response_code = resp.getcode()
                    queue_location = resp.headers.get("Location", "")
                    class MockResponse:
                        def __init__(self, code):
                            self.status_code = code
                    response = MockResponse(response_code)
            
            if response.status_code in (200, 201, 202):
                job_url = f"{jenkins_url}/job/{job_name}"
                run_id = queue_location.split("/")[-2] if queue_location else "queued"
                logger.info(f"[GenesisCICD] Jenkins build triggered: {job_name}")
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
            logger.error(f"[GenesisCICD] Jenkins trigger failed: {e}")
            return {
                "triggered": False,
                "run_id": None,
                "url": None,
                "error": str(e)
            }

    def learn_from_pipeline_outcome(
        self,
        genesis_key_id: str,
        pipeline_result: Dict[str, Any]
    ):
        """
        Learn from CI/CD pipeline outcome to improve future test selection.
        
        This is how Grace gets smarter over time.
        """
        try:
            # Get the Genesis Key
            genesis_key = self.session.query(GenesisKey).filter_by(
                key_id=genesis_key_id
            ).first()
            
            if not genesis_key:
                logger.warning(f"[GenesisCICD] Genesis Key {genesis_key_id} not found for learning")
                return

            # Extract learning data
            tests_run = pipeline_result.get("tests_run", [])
            tests_passed = pipeline_result.get("tests_passed", [])
            tests_failed = pipeline_result.get("tests_failed", [])
            duration = pipeline_result.get("duration", 0.0)

            # Update test metrics
            for test_id in tests_run:
                passed = test_id in tests_passed
                self.test_selector.record_test_result(
                    test_id=test_id,
                    passed=passed,
                    duration=duration / len(tests_run) if tests_run else 0.0
                )

            logger.info(
                f"[GenesisCICD] Learned from pipeline outcome: "
                f"{len(tests_passed)}/{len(tests_run)} tests passed"
            )

        except Exception as e:
            logger.error(f"[GenesisCICD] Error learning from outcome: {e}")

    def get_integration_stats(self) -> Dict[str, Any]:
        """Get statistics about Genesis-CI/CD integration."""
        return {
            "integrations_count": self.integrations_count,
            "test_selector_stats": {
                "total_tests_tracked": len(self.test_selector.test_metrics),
                "selection_history_count": len(self.test_selector.selection_history)
            }
        }


# Global instance
_integration: Optional[GenesisCICDIntegration] = None


def get_genesis_cicd_integration(
    session: Optional[Session] = None,
    base_path: Optional[str] = None
) -> GenesisCICDIntegration:
    """Get or create global Genesis-CI/CD integration instance."""
    global _integration
    if _integration is None or session is not None or base_path is not None:
        if session is None:
            from database.session import SessionLocal
            session = SessionLocal()
        _integration = GenesisCICDIntegration(session=session, base_path=base_path)
    return _integration
