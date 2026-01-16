"""
CI/CD Pipeline Integration with Proactive Self-Healing

Integrates Grace's proactive self-healing into CI/CD pipeline stages.
Runs proactive checks at each stage to prevent issues before they occur.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from cicd.proactive_self_healing import ProactiveSelfHealing, PipelineStage
from cognitive.devops_healing_agent import get_devops_healing_agent
from llm_orchestrator.llm_orchestrator import LLMOrchestrator
from embedding import get_embedding_model
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.session import initialize_session_factory, get_db

logger = logging.getLogger(__name__)


def initialize_proactive_healing() -> Optional[ProactiveSelfHealing]:
    """Initialize proactive self-healing system."""
    try:
        # Initialize database
        db_config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            database_path="data/grace.db"
        )
        DatabaseConnection.initialize(db_config)
        initialize_session_factory()
        session = next(get_db())
        
        # Initialize DevOps agent
        knowledge_base_path = Path("knowledge_base").resolve()
        ai_research_path = Path("data/ai_research")
        
        devops_agent = get_devops_healing_agent(
            session=session,
            knowledge_base_path=knowledge_base_path,
            ai_research_path=ai_research_path
        )
        
        # Initialize LLM orchestrator
        try:
            embedding_model = get_embedding_model()
            llm_orchestrator = LLMOrchestrator(
                session=session,
                embedding_model=embedding_model,
                knowledge_base_path=str(knowledge_base_path)
            )
        except Exception as e:
            logger.warning(f"LLM orchestrator unavailable: {e}")
            llm_orchestrator = None
        
        # Create proactive healing system
        proactive_healing = ProactiveSelfHealing(
            devops_agent=devops_agent,
            llm_orchestrator=llm_orchestrator,
            session=session
        )
        
        logger.info("[CICD] Proactive self-healing initialized")
        return proactive_healing
        
    except Exception as e:
        logger.error(f"[CICD] Failed to initialize proactive healing: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_pre_commit_check() -> int:
    """Run proactive checks before commit."""
    logger.info("=" * 80)
    logger.info("PROACTIVE SELF-HEALING - PRE-COMMIT CHECK")
    logger.info("=" * 80)
    
    proactive_healing = initialize_proactive_healing()
    if not proactive_healing:
        logger.error("Failed to initialize proactive healing")
        return 1
    
    result = proactive_healing.run_pipeline_check(
        stage=PipelineStage.PRE_COMMIT,
        context={"git_branch": "current", "git_commit": "pending"}
    )
    
    if result["issues_found"] > 0:
        logger.warning(f"Found {result['issues_found']} issues before commit")
        if result["issues_fixed"] > 0:
            logger.info(f"Fixed {result['issues_fixed']} issues proactively")
        
        # If critical issues remain unfixed, fail the check
        critical_unfixed = [
            issue for issue in result["issues"]
            if issue.get("severity") == "critical" and
            not any(fix["issue"] == issue for fix in result["fixes"])
        ]
        
        if critical_unfixed:
            logger.error(f"Critical issues remain unfixed: {len(critical_unfixed)}")
            return 1
    
    logger.info("Pre-commit check passed")
    return 0


def run_pre_build_check() -> int:
    """Run proactive checks before build."""
    logger.info("=" * 80)
    logger.info("PROACTIVE SELF-HEALING - PRE-BUILD CHECK")
    logger.info("=" * 80)
    
    proactive_healing = initialize_proactive_healing()
    if not proactive_healing:
        return 1
    
    result = proactive_healing.run_pipeline_check(
        stage=PipelineStage.PRE_BUILD
    )
    
    if result["issues_found"] > 0 and result["issues_fixed"] == 0:
        logger.error("Build-blocking issues found and not fixed")
        return 1
    
    logger.info("Pre-build check passed")
    return 0


def run_pre_test_check() -> int:
    """Run proactive checks before tests."""
    logger.info("=" * 80)
    logger.info("PROACTIVE SELF-HEALING - PRE-TEST CHECK")
    logger.info("=" * 80)
    
    proactive_healing = initialize_proactive_healing()
    if not proactive_healing:
        return 1
    
    result = proactive_healing.run_pipeline_check(
        stage=PipelineStage.PRE_TEST
    )
    
    logger.info("Pre-test check complete")
    return 0


def run_pre_deploy_check() -> int:
    """Run proactive checks before deployment."""
    logger.info("=" * 80)
    logger.info("PROACTIVE SELF-HEALING - PRE-DEPLOY CHECK")
    logger.info("=" * 80)
    
    proactive_healing = initialize_proactive_healing()
    if not proactive_healing:
        return 1
    
    result = proactive_healing.run_pipeline_check(
        stage=PipelineStage.PRE_DEPLOY
    )
    
    if result["issues_found"] > 0:
        logger.warning(f"Found {result['issues_found']} issues before deployment")
        if result["issues_fixed"] > 0:
            logger.info(f"Fixed {result['issues_fixed']} issues proactively")
    
    # Deployment should be more strict
    if result["issues_found"] > result["issues_fixed"]:
        logger.error("Deployment-blocking issues remain")
        return 1
    
    logger.info("Pre-deploy check passed")
    return 0


def run_post_deploy_check() -> int:
    """Run proactive checks after deployment."""
    logger.info("=" * 80)
    logger.info("PROACTIVE SELF-HEALING - POST-DEPLOY CHECK")
    logger.info("=" * 80)
    
    proactive_healing = initialize_proactive_healing()
    if not proactive_healing:
        return 1
    
    result = proactive_healing.run_pipeline_check(
        stage=PipelineStage.POST_DEPLOY
    )
    
    logger.info("Post-deploy check complete")
    return 0


def run_continuous_monitoring() -> None:
    """Run continuous proactive monitoring (background process)."""
    logger.info("=" * 80)
    logger.info("PROACTIVE SELF-HEALING - CONTINUOUS MONITORING")
    logger.info("=" * 80)
    
    proactive_healing = initialize_proactive_healing()
    if not proactive_healing:
        logger.error("Failed to initialize proactive healing")
        return
    
    import time
    
    logger.info("Starting continuous proactive monitoring...")
    logger.info("Checking every 60 seconds for potential issues...")
    
    while True:
        try:
            result = proactive_healing.run_pipeline_check(
                stage=PipelineStage.CONTINUOUS
            )
            
            if result["issues_found"] > 0:
                logger.info(
                    f"Continuous check: {result['issues_found']} issues found, "
                    f"{result['issues_fixed']} fixed proactively"
                )
            
            # Sleep for next check
            time.sleep(proactive_healing.continuous_check_interval)
            
        except KeyboardInterrupt:
            logger.info("Continuous monitoring stopped")
            break
        except Exception as e:
            logger.error(f"Continuous monitoring error: {e}")
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        stage = sys.argv[1]
        
        if stage == "pre-commit":
            sys.exit(run_pre_commit_check())
        elif stage == "pre-build":
            sys.exit(run_pre_build_check())
        elif stage == "pre-test":
            sys.exit(run_pre_test_check())
        elif stage == "pre-deploy":
            sys.exit(run_pre_deploy_check())
        elif stage == "post-deploy":
            sys.exit(run_post_deploy_check())
        elif stage == "continuous":
            run_continuous_monitoring()
        else:
            logger.error(f"Unknown stage: {stage}")
            sys.exit(1)
    else:
        logger.info("Usage: python pipeline_integration.py <stage>")
        logger.info("Stages: pre-commit, pre-build, pre-test, pre-deploy, post-deploy, continuous")
        sys.exit(1)
