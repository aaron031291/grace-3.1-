"""
Knowledge Indexer

Indexes ALL internal knowledge sources into the vector store
so RAG can find them. Closes the gap where Grace generates
valuable knowledge (chats, tasks, playbooks, diagnostics,
Genesis trails, feedback) but RAG can't search any of it.

Also tracks retrieval quality: which results were actually
useful vs noise.

SOURCES INDEXED:
  1. Chat conversations     → "what did we discuss about auth?"
  2. Completed tasks        → "how did we implement auth last time?"
  3. Task playbooks         → "what's the procedure for adding endpoints?"
  4. Diagnostic reports     → "what health issues happened yesterday?"
  5. Genesis Key audit trail → "who changed the auth module?"
  6. User feedback          → "which answers did users dislike?"
  7. Distilled knowledge    → high-value LLM answers re-indexed for similarity
  8. Compiled facts         → structured facts made searchable by embedding

RETRIEVAL QUALITY:
  Tracks which retrieved chunks appear in final responses.
  Feeds confidence scorer to adjust document quality over time.
"""

import logging
import hashlib
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class KnowledgeIndexer:
    """
    Indexes internal knowledge sources into the vector store for RAG.

    Run periodically to keep the index fresh. Each source is indexed
    with metadata so results can be traced back to their origin.
    """

    def __init__(self, session: Session, embedding_model=None):
        self.session = session
        self.embedding_model = embedding_model
        self._index_stats = {
            "total_indexed": 0,
            "by_source": {},
            "last_run": None,
        }

    def _get_embedding_model(self):
        """Lazy-load embedding model."""
        if self.embedding_model:
            return self.embedding_model
        try:
            from embedding import get_embedding_model
            self.embedding_model = get_embedding_model()
            return self.embedding_model
        except Exception:
            return None

    def index_all_sources(self, since_hours: int = 24) -> Dict[str, Any]:
        """
        Index all internal knowledge sources from the last N hours.

        Each source creates searchable vector entries that RAG can find.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        results = {}

        results["chats"] = self._index_chat_history(cutoff)
        results["tasks"] = self._index_completed_tasks(cutoff)
        results["playbooks"] = self._index_playbooks()
        results["diagnostics"] = self._index_diagnostic_reports(cutoff)
        results["genesis"] = self._index_genesis_keys(cutoff)
        results["feedback"] = self._index_user_feedback(cutoff)
        results["distilled"] = self._index_distilled_knowledge()

        total = sum(r.get("indexed", 0) for r in results.values())
        self._index_stats["total_indexed"] += total
        self._index_stats["last_run"] = datetime.now(timezone.utc).isoformat()

        for source, result in results.items():
            self._index_stats["by_source"][source] = (
                self._index_stats["by_source"].get(source, 0) + result.get("indexed", 0)
            )

        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "knowledge_indexer",
                f"Indexed {total} entries from {len(results)} sources",
                data=results,
            )
        except Exception:
            pass

        logger.info(f"[INDEXER] Indexed {total} entries from {len(results)} sources")

        return {"total_indexed": total, "sources": results}

    def _store_in_vector_db(self, text: str, metadata: Dict[str, Any]) -> bool:
        """Embed text and store in Qdrant vector DB."""
        model = self._get_embedding_model()
        if not model:
            return False

        try:
            from vector_db.client import get_qdrant_client
            from models.database_models import Document, DocumentChunk

            embedding = model.embed_text([text])[0]
            qdrant = get_qdrant_client()

            vector_id = hashlib.md5(text[:500].encode()).hexdigest()

            qdrant.upsert_vectors(
                collection_name="documents",
                vectors=[embedding],
                ids=[vector_id],
                payloads=[metadata],
            )

            return True
        except Exception as e:
            logger.debug(f"[INDEXER] Vector storage failed: {e}")
            return False

    def _index_chat_history(self, cutoff: datetime) -> Dict[str, Any]:
        """Index recent chat conversations."""
        indexed = 0
        try:
            from models.database_models import Chat

            chats = self.session.query(Chat).filter(
                Chat.created_at >= cutoff
            ).limit(200).all()

            for chat in chats:
                user_msg = getattr(chat, 'user_message', '') or ''
                assistant_msg = getattr(chat, 'assistant_message', '') or getattr(chat, 'response', '') or ''

                if user_msg and len(user_msg) > 10:
                    text = f"Q: {user_msg}\nA: {assistant_msg}"
                    if self._store_in_vector_db(text[:2000], {
                        "source": "chat_history",
                        "type": "conversation",
                        "chat_id": str(getattr(chat, 'id', '')),
                        "timestamp": str(getattr(chat, 'created_at', '')),
                    }):
                        indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Chat indexing error: {e}")

        return {"indexed": indexed, "source": "chat_history"}

    def _index_completed_tasks(self, cutoff: datetime) -> Dict[str, Any]:
        """Index completed task records."""
        indexed = 0
        try:
            from cognitive.task_completion_verifier import VerifiedTask

            tasks = self.session.query(VerifiedTask).filter(
                VerifiedTask.status == "complete",
                VerifiedTask.completed_at >= cutoff,
            ).limit(100).all()

            for task in tasks:
                text = (
                    f"Task: {task.title}\n"
                    f"Type: {task.task_type}\n"
                    f"Criteria: {len(task.completion_criteria or [])} items\n"
                    f"Verification attempts: {task.verification_attempts}\n"
                    f"Duration: {task.actual_duration_minutes} minutes"
                )
                if self._store_in_vector_db(text, {
                    "source": "completed_task",
                    "type": "task_record",
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                }):
                    indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Task indexing error: {e}")

        return {"indexed": indexed, "source": "completed_tasks"}

    def _index_playbooks(self) -> Dict[str, Any]:
        """Index task playbooks."""
        indexed = 0
        try:
            from cognitive.task_playbook_engine import TaskPlaybook

            playbooks = self.session.query(TaskPlaybook).filter(
                TaskPlaybook.confidence >= 0.5
            ).limit(100).all()

            for pb in playbooks:
                steps_text = ""
                for step in (pb.steps or []):
                    steps_text += f"\n  Step {step.get('order', '?')}: {step.get('action', '')}"

                text = f"Playbook: {pb.name}\nGoal: {pb.description or ''}{steps_text}"

                if self._store_in_vector_db(text[:2000], {
                    "source": "playbook",
                    "type": "procedure",
                    "playbook_id": pb.playbook_id,
                    "success_rate": pb.success_rate,
                }):
                    indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Playbook indexing error: {e}")

        return {"indexed": indexed, "source": "playbooks"}

    def _index_diagnostic_reports(self, cutoff: datetime) -> Dict[str, Any]:
        """Index diagnostic cycle summaries."""
        indexed = 0
        try:
            from models.llm_tracking_models import LLMInteraction

            diagnostics = self.session.query(LLMInteraction).filter(
                LLMInteraction.model_used == "diagnostic_engine",
                LLMInteraction.created_at >= cutoff,
            ).limit(100).all()

            for diag in diagnostics:
                text = f"Diagnostic: {diag.prompt}\nResult: {diag.response}"
                if self._store_in_vector_db(text[:2000], {
                    "source": "diagnostic",
                    "type": "health_report",
                    "interaction_id": diag.interaction_id,
                }):
                    indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Diagnostic indexing error: {e}")

        return {"indexed": indexed, "source": "diagnostics"}

    def _index_genesis_keys(self, cutoff: datetime) -> Dict[str, Any]:
        """Index Genesis Key provenance records."""
        indexed = 0
        try:
            from models.genesis_key_models import GenesisKey

            keys = self.session.query(GenesisKey).filter(
                GenesisKey.created_at >= cutoff,
            ).limit(200).all()

            for gk in keys:
                desc = getattr(gk, 'what_description', '') or ''
                if desc and len(desc) > 10:
                    text = f"Genesis: {desc}\nType: {gk.key_type.value if hasattr(gk.key_type, 'value') else gk.key_type}"
                    if self._store_in_vector_db(text[:1000], {
                        "source": "genesis_key",
                        "type": "audit_trail",
                        "key_id": gk.key_id,
                    }):
                        indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Genesis indexing error: {e}")

        return {"indexed": indexed, "source": "genesis_keys"}

    def _index_user_feedback(self, cutoff: datetime) -> Dict[str, Any]:
        """Index user feedback on responses."""
        indexed = 0
        try:
            from models.llm_tracking_models import LLMInteraction

            feedback = self.session.query(LLMInteraction).filter(
                LLMInteraction.model_used == "user_feedback",
                LLMInteraction.created_at >= cutoff,
            ).limit(100).all()

            for fb in feedback:
                text = f"Feedback: {fb.user_feedback} on: {fb.prompt[:200]}\nResponse: {fb.response[:200]}"
                if self._store_in_vector_db(text[:1000], {
                    "source": "user_feedback",
                    "type": "feedback",
                    "feedback": fb.user_feedback,
                }):
                    indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Feedback indexing error: {e}")

        return {"indexed": indexed, "source": "user_feedback"}

    def _index_distilled_knowledge(self) -> Dict[str, Any]:
        """Index high-confidence distilled knowledge for similarity search."""
        indexed = 0
        try:
            from cognitive.knowledge_compiler import DistilledKnowledge

            entries = self.session.query(DistilledKnowledge).filter(
                DistilledKnowledge.confidence >= 0.7,
            ).limit(200).all()

            for entry in entries:
                text = f"Q: {entry.query_text}\nA: {entry.response_text[:500]}"
                if self._store_in_vector_db(text[:2000], {
                    "source": "distilled_knowledge",
                    "type": "qa_pair",
                    "confidence": entry.confidence,
                    "verified": entry.is_verified,
                    "query_hash": entry.query_hash,
                }):
                    indexed += 1

        except Exception as e:
            logger.debug(f"[INDEXER] Distilled indexing error: {e}")

        return {"indexed": indexed, "source": "distilled_knowledge"}

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._index_stats)


class RetrievalQualityTracker:
    """
    Tracks which retrieved results were actually useful.

    When a response is generated, compare the retrieved chunks
    against what appears in the final response. Chunks that
    contributed get boosted. Chunks that were retrieved but
    ignored get noted.

    Over time, this improves retrieval quality by:
    - Feeding hit/miss rates to confidence scorer
    - Identifying documents that are frequently retrieved but never useful
    - Identifying documents that should rank higher
    """

    def __init__(self, session: Session):
        self.session = session
        self._hit_counts: Dict[str, int] = {}
        self._miss_counts: Dict[str, int] = {}

    def record_retrieval_usage(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        final_response: str,
    ):
        """
        Compare retrieved chunks against the final response.

        Chunks whose text appears in the response = HIT.
        Chunks not reflected in response = MISS.
        """
        response_lower = final_response.lower()

        for chunk in retrieved_chunks:
            chunk_text = chunk.get("text", "")
            chunk_id = str(chunk.get("chunk_id", chunk.get("document_id", "")))

            if not chunk_text or not chunk_id:
                continue

            # Check if key phrases from the chunk appear in the response
            words = chunk_text.lower().split()
            key_phrases = [" ".join(words[i:i+4]) for i in range(0, min(len(words), 20), 4)]

            hits = sum(1 for phrase in key_phrases if phrase in response_lower)
            is_useful = hits >= 1

            if is_useful:
                self._hit_counts[chunk_id] = self._hit_counts.get(chunk_id, 0) + 1
            else:
                self._miss_counts[chunk_id] = self._miss_counts.get(chunk_id, 0) + 1

            # Feed back to confidence scorer
            try:
                from models.database_models import DocumentChunk
                db_chunk = self.session.query(DocumentChunk).filter(
                    DocumentChunk.id == int(chunk_id) if chunk_id.isdigit() else False
                ).first()

                if db_chunk and hasattr(db_chunk, 'confidence_score'):
                    if is_useful:
                        db_chunk.confidence_score = min(1.0, (db_chunk.confidence_score or 0.5) + 0.01)
                    else:
                        db_chunk.confidence_score = max(0.1, (db_chunk.confidence_score or 0.5) - 0.005)
            except Exception:
                pass

    def get_quality_report(self) -> Dict[str, Any]:
        """Get retrieval quality statistics."""
        total_hits = sum(self._hit_counts.values())
        total_misses = sum(self._miss_counts.values())
        total = total_hits + total_misses

        return {
            "total_retrievals_tracked": total,
            "useful_results": total_hits,
            "unused_results": total_misses,
            "usefulness_rate": total_hits / total if total > 0 else 0,
            "top_useful_chunks": sorted(
                self._hit_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "top_wasted_chunks": sorted(
                self._miss_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }


_indexer: Optional[KnowledgeIndexer] = None
_quality_tracker: Optional[RetrievalQualityTracker] = None


def get_knowledge_indexer(session: Session) -> KnowledgeIndexer:
    global _indexer
    if _indexer is None:
        _indexer = KnowledgeIndexer(session)
    return _indexer


def get_retrieval_quality_tracker(session: Session) -> RetrievalQualityTracker:
    global _quality_tracker
    if _quality_tracker is None:
        _quality_tracker = RetrievalQualityTracker(session)
    return _quality_tracker
