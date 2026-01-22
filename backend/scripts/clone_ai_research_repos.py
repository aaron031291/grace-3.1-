"""
Script to clone all AI research repositories from GitHub for Grace's training data.

This script clones all repositories listed in the documentation into the appropriate
directory structure for ingestion.

Usage:
    # Without GitHub token (subject to rate limits):
    python backend/scripts/clone_ai_research_repos.py
    
    # With GitHub token (recommended):
    # 1. Set GITHUB_TOKEN environment variable:
    export GITHUB_TOKEN=ghp_your_token_here  # Linux/macOS
    set GITHUB_TOKEN=ghp_your_token_here     # Windows CMD
    $env:GITHUB_TOKEN="ghp_your_token_here"  # Windows PowerShell
    
    # 2. Or add to backend/.env file:
    GITHUB_TOKEN=ghp_your_token_here
    
    # 3. Then run the script:
    python backend/scripts/clone_ai_research_repos.py

GitHub Token Setup:
    1. Generate a token at: https://github.com/settings/tokens
    2. Select scopes: 'public_repo' (or 'repo' for private repos)
    3. Copy the token and set it in your environment or .env file
    
Benefits of using a GitHub token:
    - Increased API rate limits (5,000/hour vs 60 for anonymous)
    - Access to private repositories (if needed)
    - Avoid rate limiting when cloning many repositories
"""

import os
import sys
import subprocess
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed. Environment variables must be set manually.")


# Repository definitions by category
REPOSITORIES = {
    # Original AI/ML repositories
    "frameworks": [
        ("vllm-project/aibrix", "aibrix"),
        ("infiniflow/ragflow", "ragflow"),
        ("langchain-ai/langgraph", "langgraph"),
        ("langgenius/dify", "dify"),
        ("TransformerOptimus/SuperAGI", "SuperAGI"),
        ("OpenDevin/OpenDevin", "OpenDevin"),
        ("deepset-ai/haystack", "haystack"),
        ("neuro-symbolic-ai/peirce", "peirce"),
    ],
    "enterprise": [
        ("odoo/odoo", "odoo"),
        ("frappe/erpnext", "erpnext"),
    ],
    "infrastructure": [
        ("kubernetes/kubernetes", "kubernetes"),
        ("apache/kafka", "kafka"),
        ("apache/cassandra", "cassandra"),
    ],
    "references": [
        ("binhnguyennus/awesome-scalability", "awesome-scalability"),
    ],
    "education": [
        ("freeCodeCamp/freeCodeCamp", "freeCodeCamp"),
        ("microsoft/generative-ai-for-beginners", "generative-ai-for-beginners"),
    ],
    "ai_ml_advanced": [
        ("run-llama/llama_index", "llama_index"),
        ("huggingface/transformers", "transformers"),
        ("pytorch/pytorch", "pytorch"),
        ("microsoft/autogen", "autogen"),
    ],
    "web_development": [
        ("vercel/next.js", "next.js"),
        ("django/django", "django"),
        ("fastapi/fastapi", "fastapi"),
    ],
    "databases": [
        ("postgres/postgres", "postgres"),
        ("redis/redis", "redis"),
        ("duckdb/duckdb", "duckdb"),
    ],
    "languages": [
        ("python/cpython", "cpython"),
        ("rust-lang/rust", "rust"),
        ("golang/go", "go"),
    ],
    "devops": [
        ("hashicorp/terraform", "terraform"),
        ("grafana/grafana", "grafana"),
    ],
    "scientific": [
        ("numpy/numpy", "numpy"),
        ("pandas-dev/pandas", "pandas"),
        ("scikit-learn/scikit-learn", "scikit-learn"),
        ("matplotlib/matplotlib", "matplotlib"),
    ],
    "security": [
        ("OWASP/CheatSheetSeries", "CheatSheetSeries"),
    ],
    "awesome_lists": [
        ("sindresorhus/awesome", "awesome"),
        ("awesome-selfhosted/awesome-selfhosted", "awesome-selfhosted"),
        ("avelino/awesome-go", "awesome-go"),
        ("vinta/awesome-python", "awesome-python"),
        ("enaqx/awesome-react", "awesome-react"),
    ],
    # NEW: 50 Enterprise Repositories for Complete Software Engineering Immersion
    "web_frontend": [
        ("facebook/react", "react"),
        ("vuejs/vue", "vue"),
        ("angular/angular", "angular"),
        ("sveltejs/svelte", "svelte"),
        ("microsoft/TypeScript", "TypeScript"),
    ],
    "web_backend": [
        ("spring-projects/spring-boot", "spring-boot"),
        ("expressjs/express", "express"),
        ("gin-gonic/gin", "gin"),
        ("actix/actix-web", "actix-web"),
        ("ruby-on-rails/rails", "rails"),
    ],
    "mobile": [
        ("facebook/react-native", "react-native"),
        ("flutter/flutter", "flutter"),
        ("apple/swift", "swift"),
    ],
    "cloud_infrastructure": [
        ("hashicorp/consul", "consul"),
        ("etcd-io/etcd", "etcd"),
        ("envoyproxy/envoy", "envoy"),
        ("traefik/traefik", "traefik"),
        ("istio/istio", "istio"),
    ],
    "data_analytics": [
        ("apache/spark", "spark"),
        ("apache/flink", "flink"),
        ("apache/airflow", "airflow"),
        ("prestodb/presto", "presto"),
        ("apache/druid", "druid"),
    ],
    "ml_ai_frameworks": [
        ("tensorflow/tensorflow", "tensorflow"),
        ("apache/mxnet", "mxnet"),
        ("ray-project/ray", "ray"),
        ("wandb/client", "wandb"),
    ],
    "databases_enterprise": [
        ("mongodb/mongo", "mongo"),
        ("cockroachdb/cockroach", "cockroach"),
        ("ClickHouse/ClickHouse", "ClickHouse"),
        ("tikv/tikv", "tikv"),
    ],
    "devops_cicd": [
        ("jenkinsci/jenkins", "jenkins"),
        ("gitlabhq/gitlab-ce", "gitlab-ce"),
        ("harness/drone", "drone"),
        ("argoproj/argo-cd", "argo-cd"),
    ],
    "monitoring_observability": [
        ("prometheus/prometheus", "prometheus"),
        ("jaegertracing/jaeger", "jaeger"),
        ("elastic/elasticsearch", "elasticsearch"),
    ],
    "security_enterprise": [
        ("hashicorp/vault", "vault"),
        ("aquasecurity/trivy", "trivy"),
        ("falcosecurity/falco", "falco"),
    ],
    "testing_enterprise": [
        ("SeleniumHQ/selenium", "selenium"),
        ("locustio/locust", "locust"),
        ("facebook/jest", "jest"),
    ],
    "cms_ecommerce": [
        ("strapi/strapi", "strapi"),
        ("magento/magento2", "magento2"),
    ],
    "blockchain_distributed": [
        ("ethereum/go-ethereum", "go-ethereum"),
        ("ipfs/go-ipfs", "go-ipfs"),
    ],
    "messaging": [
        ("apache/pulsar", "pulsar"),
    ],
}


def get_github_token() -> Optional[str]:
    """
    Get GitHub personal access token from environment variable.
    
    Returns:
        GitHub token if set, None otherwise
    """
    token = os.getenv('GITHUB_TOKEN', '').strip()
    if token:
        logger.info("GitHub token found - using authenticated requests")
        return token
    else:
        logger.warning("No GitHub token found - using anonymous requests (subject to rate limits)")
        logger.warning("To use authenticated requests, set GITHUB_TOKEN environment variable")
        logger.warning("Generate token at: https://github.com/settings/tokens")
        return None


def build_git_url(repo_url: str, github_token: Optional[str] = None) -> str:
    """
    Build a git URL for cloning from GitHub.
    
    Args:
        repo_url: GitHub repository URL (owner/repo format)
        github_token: Optional GitHub personal access token for authentication
    
    Returns:
        Full git URL with or without authentication
    """
    if github_token:
        return f"https://{github_token}@github.com/{repo_url}.git"
    else:
        return f"https://github.com/{repo_url}.git"


def sanitize_error_message(error_msg: str, github_token: Optional[str]) -> str:
    """
    Remove any token references from error messages for security.
    
    Args:
        error_msg: The error message to sanitize
        github_token: The token to remove from the message
    
    Returns:
        Sanitized error message
    """
    if not github_token:
        return error_msg
    
    # Remove token from error messages using multiple patterns
    # Pattern 1: Token in HTTPS URLs (https://TOKEN@github.com)
    error_msg = error_msg.replace(f"https://{github_token}@", "https://***TOKEN***@")
    
    # Pattern 2: Token in SSH-style URLs (though less common for tokens)
    # git@github.com:TOKEN/repo or similar patterns
    error_msg = error_msg.replace(f":{github_token}/", ":***TOKEN***/")
    error_msg = error_msg.replace(f":{github_token}@", ":***TOKEN***@")
    
    # Pattern 3: Token as URL parameter (token=...)
    error_msg = re.sub(f"token={re.escape(github_token)}", "token=***TOKEN***", error_msg, flags=re.IGNORECASE)
    
    # Pattern 4: Token in Authorization headers
    error_msg = re.sub(f"Authorization:.*{re.escape(github_token)}", "Authorization: ***TOKEN***", error_msg, flags=re.IGNORECASE)
    
    # Pattern 5: Direct token match (case-insensitive) - catch any remaining occurrences
    error_msg = re.sub(re.escape(github_token), "***TOKEN***", error_msg, flags=re.IGNORECASE)
    
    # Pattern 6: Partial token matches (in case of truncation) - first 8 characters
    if len(github_token) > 8:
        token_prefix = github_token[:8]
        error_msg = re.sub(re.escape(token_prefix) + r'\w*', "***TOKEN***", error_msg, flags=re.IGNORECASE)
    
    return error_msg


def clone_repository(
    repo_url: str,
    target_path: Path,
    repo_name: str,
    depth: int = 1,
    github_token: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Clone a repository from GitHub.
    
    Args:
        repo_url: GitHub repository URL (owner/repo format)
        target_path: Path where repository should be cloned
        repo_name: Local directory name for the repository
        depth: Git clone depth (1 = shallow clone, None = full clone)
        github_token: Optional GitHub personal access token for authentication
    
    Returns:
        (success, message)
    """
    clone_path = target_path / repo_name
    
    # Check if already exists
    if clone_path.exists():
        logger.info(f"Repository already exists: {repo_name}")
        return True, "Already exists"
    
    try:
        # Create parent directory
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Build the URL using helper function
        full_url = build_git_url(repo_url, github_token)
        
        # Build git clone command
        cmd = ["git", "clone"]
        
        # Add depth for shallow clone (faster, less disk space)
        if depth:
            cmd.extend(["--depth", str(depth)])
        
        # Add URL and target path
        cmd.extend([full_url, str(clone_path)])
        
        # Log without token for security
        logger.info(f"Cloning {repo_url} to {clone_path}...")
        
        # Run git clone
        # Git will automatically hide credentials from error messages
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Successfully cloned {repo_name}")
            return True, "Success"
        else:
            # Sanitize error message to remove any token references
            error_msg = sanitize_error_message(result.stderr.strip(), github_token)
            logger.error(f"✗ Failed to clone {repo_name}: {error_msg}")
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = f"Timeout cloning {repo_name}"
        logger.error(f"✗ {error_msg}")
        return False, error_msg
    except Exception as e:
        # Sanitize exception message to prevent token leakage
        error_msg = f"Error cloning {repo_name}: {str(e)}"
        error_msg = sanitize_error_message(error_msg, github_token)
        logger.error(f"✗ {error_msg}")
        return False, error_msg


def clone_all_repositories(
    base_path: str,
    depth: int = 1,
    categories: List[str] = None,
    github_token: Optional[str] = None
) -> Dict[str, Dict[str, any]]:
    """
    Clone all repositories.
    
    Args:
        base_path: Base path for ai_research directory
        depth: Git clone depth (1 = shallow clone)
        categories: List of categories to clone (None = all)
        github_token: Optional GitHub personal access token for authentication
    
    Returns:
        Statistics dictionary
    """
    base_path = Path(base_path)
    ai_research_path = base_path / "ai_research"
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Cloning AI Research Repositories")
    logger.info(f"Base path: {ai_research_path}")
    logger.info(f"Clone depth: {depth} ({'shallow' if depth else 'full'})")
    logger.info(f"Authentication: {'Enabled (using token)' if github_token else 'Anonymous (rate limited)'}")
    logger.info(f"{'='*80}\n")
    
    stats = {
        "total_repos": 0,
        "cloned": 0,
        "already_exists": 0,
        "failed": 0,
        "by_category": {},
    }
    
    categories_to_process = categories or list(REPOSITORIES.keys())
    
    for category in categories_to_process:
        if category not in REPOSITORIES:
            logger.warning(f"Unknown category: {category}")
            continue
        
        category_path = ai_research_path / category
        category_stats = {
            "total": len(REPOSITORIES[category]),
            "cloned": 0,
            "already_exists": 0,
            "failed": 0,
        }
        
        logger.info(f"\n{'*'*80}")
        logger.info(f"Category: {category.upper()}")
        logger.info(f"{'*'*80}\n")
        
        for repo_url, repo_name in REPOSITORIES[category]:
            stats["total_repos"] += 1
            
            success, message = clone_repository(
                repo_url=repo_url,
                target_path=category_path,
                repo_name=repo_name,
                depth=depth,
                github_token=github_token
            )
            
            if success:
                if message == "Already exists":
                    category_stats["already_exists"] += 1
                    stats["already_exists"] += 1
                else:
                    category_stats["cloned"] += 1
                    stats["cloned"] += 1
            else:
                category_stats["failed"] += 1
                stats["failed"] += 1
        
        stats["by_category"][category] = category_stats
    
    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info(f"CLONING SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total repositories: {stats['total_repos']}")
    logger.info(f"Successfully cloned: {stats['cloned']}")
    logger.info(f"Already existed: {stats['already_exists']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"{'='*80}\n")
    
    for category, cat_stats in stats["by_category"].items():
        logger.info(
            f"{category}: {cat_stats['cloned']} cloned, "
            f"{cat_stats['already_exists']} existed, "
            f"{cat_stats['failed']} failed"
        )
    
    return stats


def main():
    """Main entry point."""
    # Get project root (parent of backend)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent
    base_path = project_root / "data"
    
    # Check if git is available
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Git is not installed or not in PATH")
        sys.exit(1)
    
    # Get GitHub token from environment
    github_token = get_github_token()
    
    # Clone repositories
    # Use depth=1 for shallow clones (faster, less disk space)
    # Set depth=None for full clones (if you need full history)
    stats = clone_all_repositories(
        base_path=str(base_path),
        depth=1,  # Shallow clone for faster setup
        categories=None,  # Clone all categories
        github_token=github_token
    )
    
    if stats["failed"] > 0:
        logger.warning(f"\n⚠️  {stats['failed']} repositories failed to clone")
        logger.warning("Check the logs above for error messages")
        sys.exit(1)
    else:
        logger.info("\n✓ All repositories cloned successfully!")
        logger.info(f"\nNext step: Run ingestion script:")
        logger.info(f"  python backend/scripts/ingest_ai_research_repos.py")


if __name__ == "__main__":
    main()
