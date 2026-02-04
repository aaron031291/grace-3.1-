"""Quick verification that learning subagents initialize in lightweight mode.

This is intentionally a simple, direct-execution script (no pytest).
It should work even when no embedding model, Qdrant, or Ollama is available.

Run:
  python backend/test_learning_subagent_bases.py
"""

import logging
from pathlib import Path
from multiprocessing import Queue, Manager

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    from database.config import DatabaseConfig
    from database.connection import DatabaseConnection
    from database.session import initialize_session_factory

    # Ensure DB engine/session factory exist (subagents rely on it)
    db_config = DatabaseConfig()
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()

    from cognitive.learning_subagent_system import StudySubagent, PracticeSubagent

    kb_path = str(Path("backend/knowledge_base").resolve())

    manager = Manager()
    shared = manager.dict()
    result_queue = Queue()

    study = StudySubagent(
        agent_id="study-test",
        task_queue=Queue(),
        result_queue=result_queue,
        shared_state=shared,
        knowledge_base_path=kb_path,
    )
    practice = PracticeSubagent(
        agent_id="practice-test",
        task_queue=Queue(),
        result_queue=result_queue,
        shared_state=shared,
        knowledge_base_path=kb_path,
    )

    # Call init methods directly (do not spawn processes)
    study._initialize()
    practice._initialize()

    assert hasattr(study.retriever, "retrieve")
    assert hasattr(practice.retriever, "retrieve")

    logger.info("✓ StudySubagent initialized")
    logger.info("✓ PracticeSubagent initialized")
    logger.info("OK")


if __name__ == "__main__":
    main()
