import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def ingest_recent_validations():
    """
    Ingest recent successful validations from MongoDB into Magma memory.
    This creates learning points for the autonomous loop and coding agent.
    """
    try:
        from database.mongo_client import get_db
        db = get_db()
        if db is None:
            logger.warning("[INGEST] MongoDB not configured. Skipping validation ingestion.")
            return 0
            
        collection = db["validation_results"]
        # Find successful validations from the last 24 hours that haven't been ingested
        # For simplicity in this script, we just pull the top 10 most recent successful ones
        recent_successes = collection.find({"status": "success"}).sort("completed_at", -1).limit(10)
        
        from cognitive import magma_bridge as magma
        
        count = 0
        for doc in recent_successes:
            task_id = doc.get("task_id", "unknown")
            target = doc.get("target", "unknown")
            stages = doc.get("stages", [])
            
            # Format learning content
            stage_summaries = ", ".join([f"{s['stage']} ({s.get('score', 100)})" for s in stages])
            content = f"Successful Validation Run [{task_id}] on {target}. Stages passed: {stage_summaries}."
            
            # Ingest into Magma
            magma.ingest(
                content,
                source="validation_pipeline",
                metadata={"task_id": task_id, "target": target, "type": "validation_success"}
            )
            count += 1
            
        logger.info(f"[INGEST] Ingested {count} recent successful validations into Magma memory.")
        return count
        
    except Exception as e:
        logger.error(f"[INGEST] Failed to ingest validations: {e}")
        return 0

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_recent_validations()
