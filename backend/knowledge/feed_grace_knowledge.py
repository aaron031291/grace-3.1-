"""
Feed Grace the Knowledge She Needs - Main Entry Point

Automatically feeds Grace knowledge based on stress test results:
1. Identifies knowledge gaps
2. Finds GitHub repos
3. Ingests enterprise data
4. Feeds AI research
5. Enables LLM bidirectional communication
6. Tests in sandbox
7. Uses DeepSeek with governance

Usage:
    python -m backend.knowledge.feed_grace_knowledge [stress_test_report.json]
"""

import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from database.session import initialize_session_factory, get_session
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from knowledge.grace_knowledge_feeder import get_grace_knowledge_feeder
from communication.grace_llm_bridge import get_grace_llm_bridge
from llm_orchestrator.llm_orchestrator import LLMOrchestrator
from embedding import get_embedding_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def feed_grace_from_stress_test(report_file: Path):
    """Feed Grace knowledge based on stress test report."""
    logger.info(f"Reading stress test report: {report_file}")
    
    # Load report
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    # Initialize database
    db_config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database_path="data/grace.db"
    )
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    
    session = get_session()
    
    try:
        # Initialize components
        embedding_model = get_embedding_model()
        llm_orchestrator = LLMOrchestrator(
            session=session,
            embedding_model=embedding_model,
            knowledge_base_path="backend/knowledge_base"
        )
        
        # Initialize knowledge feeder
        feeder = get_grace_knowledge_feeder(
            session=session,
            knowledge_base_path=Path("backend/knowledge_base")
        )
        feeder.llm_orchestrator = llm_orchestrator
        
        # Initialize LLM bridge
        bridge = get_grace_llm_bridge(
            session=session,
            llm_orchestrator=llm_orchestrator
        )
        await bridge.start()
        
        # Get knowledge gaps from report
        knowledge_gaps = report.get("knowledge_gaps", {})
        identified_gaps = knowledge_gaps.get("identified_gaps", [])
        recommendations = knowledge_gaps.get("recommendations", [])
        
        logger.info(f"Found {len(identified_gaps)} knowledge gaps")
        
        # Feed knowledge from gaps
        if identified_gaps:
            logger.info("=" * 80)
            logger.info("FEEDING GRACE KNOWLEDGE FROM GAPS")
            logger.info("=" * 80)
            
            feed_result = await feeder.feed_knowledge_from_gaps(
                identified_gaps,
                priority="high"
            )
            
            logger.info(f"Knowledge feeding complete:")
            logger.info(f"  - Gaps processed: {feed_result['gaps_processed']}")
            logger.info(f"  - Repos ingested: {feed_result['repos_ingested']}")
            logger.info(f"  - Files ingested: {feed_result['files_ingested']}")
            logger.info(f"  - LLM queries: {feed_result['llm_queries']}")
            logger.info(f"  - Sandbox tests: {feed_result['sandbox_tests']}")
        
        # Feed AI research
        research_topics = [gap.get("topic", "") for gap in identified_gaps[:5]]
        if research_topics:
            logger.info("=" * 80)
            logger.info("FEEDING GRACE AI RESEARCH")
            logger.info("=" * 80)
            
            research_result = await feeder.feed_ai_research(research_topics)
            
            logger.info(f"AI research feeding complete:")
            logger.info(f"  - Topics processed: {research_result['topics_processed']}")
            logger.info(f"  - Repos cloned: {research_result['repos_cloned']}")
            logger.info(f"  - Files ingested: {research_result['files_ingested']}")
        
        # Test bidirectional communication
        logger.info("=" * 80)
        logger.info("TESTING BIDIRECTIONAL LLM COMMUNICATION")
        logger.info("=" * 80)
        
        # Grace asks LLM a question
        async def handle_response(response):
            logger.info(f"[CALLBACK] LLM responded: {response.content[:100]}...")
            logger.info(f"[CALLBACK] Trust score: {response.trust_score}, Verified: {response.verified}")
        
        message_id = await bridge.grace_asks_llm(
            question="What are the best practices for fixing database schema errors?",
            context={"topic": "database", "priority": "high"},
            callback=handle_response,
            use_deepseek=True
        )
        
        # Wait for response
        response = await bridge.wait_for_response(message_id, timeout=30.0)
        if response:
            logger.info(f"✅ Received LLM response: {response.content[:200]}...")
            logger.info(f"   Trust: {response.trust_score}, Verified: {response.verified}")
        
        await bridge.stop()
        
        logger.info("=" * 80)
        logger.info("KNOWLEDGE FEEDING COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Knowledge feeding failed: {e}", exc_info=True)
        raise
    finally:
        session.close()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        report_file = Path(sys.argv[1])
    else:
        # Find most recent report
        reports = sorted(Path(".").glob("stress_test_report_*.json"), reverse=True)
        if not reports:
            print("No stress test report found. Run stress_test_self_healing.py first.")
            return
        report_file = reports[0]
    
    if not report_file.exists():
        print(f"Report file not found: {report_file}")
        return
    
    # Run async
    asyncio.run(feed_grace_from_stress_test(report_file))


if __name__ == "__main__":
    main()
