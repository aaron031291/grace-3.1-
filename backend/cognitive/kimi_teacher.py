"""
Kimi Teacher - Cloud API as Grace's Teacher

Kimi Cloud is the TEACHER. Grace is the STUDENT.
They are SEPARATE systems. Grace governs when to call Kimi.

Kimi Teacher can:
  - Mine knowledge on topics Grace doesn't know
  - Analyze Grace's source code and suggest improvements
  - Answer complex questions Grace can't handle locally
  - Extract facts/procedures/rules from text at high quality

Every Kimi output:
  - Gets a Genesis Key (full audit trail)
  - Feeds into Grace's Knowledge Compiler (facts, procedures, rules)
  - Feeds into Magma Memory (episodic recall)
  - Feeds Oracle ML (training signal)
  - Stored in Distilled Knowledge (never ask same thing twice)

GraceBrain governs ALL calls. Kimi never acts on her own.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class KimiTeacher:
    """
    Kimi Cloud as Grace's teacher.

    Separate from GraceBrain. Called BY GraceBrain when Grace
    needs to learn something she can't figure out locally.

    Every interaction:
    1. Genesis Key assigned (who/what/when/why tracked)
    2. Response compiled into knowledge store
    3. Response stored in Magma episodic memory
    4. Response feeds Oracle ML training
    5. Response cached in distilled knowledge
    """

    def __init__(self, session: Session):
        self.session = session
        self._cloud_client = None
        self._stats = {
            "total_lessons": 0,
            "total_tokens": 0,
            "topics_mined": [],
            "genesis_keys_created": 0,
        }

    def _get_cloud(self):
        """Lazy-load cloud client."""
        if self._cloud_client:
            return self._cloud_client
        try:
            from cognitive.grace_cloud_client import get_kimi_cloud_client
            self._cloud_client = get_kimi_cloud_client()
            return self._cloud_client
        except Exception:
            return None

    def _create_genesis_key(self, action: str, details: Dict[str, Any]) -> Optional[str]:
        """Create Genesis Key for every Kimi interaction."""
        try:
            from models.genesis_key_models import GenesisKey, GenesisKeyType
            gk = GenesisKey(
                key_id=f"GK-KIMI-{uuid.uuid4().hex[:12]}",
                key_type=GenesisKeyType.LEARNING,
                what_description=f"Kimi Teacher: {action}",
                who_actor="kimi_cloud",
                where_location="cloud_api",
                why_justification=f"Grace requested: {action[:200]}",
                context_data=details,
            )
            self.session.add(gk)
            self.session.flush()
            self._stats["genesis_keys_created"] += 1
            return gk.key_id
        except Exception as e:
            logger.debug(f"[KIMI-TEACHER] Genesis Key failed: {e}")
            return None

    def _store_in_magma(self, question: str, answer: str, topic: str):
        """Store in Magma episodic memory."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
            buffer = EpisodicBuffer(self.session)
            buffer.store({
                "problem": f"Kimi taught: {question[:200]}",
                "action": {"type": "kimi_teaching", "topic": topic},
                "outcome": {"success": True, "content": answer[:500]},
                "source": "kimi_teacher",
                "trust_score": 0.85,
            })
        except Exception:
            pass

    def _compile_response(self, question: str, answer: str, topic: str, genesis_key_id: str):
        """Compile Kimi's response into facts/procedures/rules."""
        try:
            from cognitive.knowledge_compiler import KnowledgeCompiler
            compiler = KnowledgeCompiler(self.session, llm_client=None)
            result = compiler.compile_chunk(
                text=answer,
                source_document_id=f"kimi_teacher:{genesis_key_id or 'unknown'}",
                domain=topic,
            )
            return result
        except Exception:
            return {}

    def _distill_response(self, question: str, answer: str, model: str):
        """Store in distilled knowledge for future deterministic serving."""
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            miner = get_llm_knowledge_miner(self.session)
            miner.store_interaction(
                query=question,
                response=answer,
                model_used=model,
                confidence=0.8,
            )
        except Exception:
            pass

    def _feed_oracle(self, question: str, answer: str, topic: str, success: bool):
        """Feed result to Oracle ML as training signal."""
        try:
            from cognitive.learning_hook import track_learning_event
            track_learning_event(
                "kimi_teacher_lesson",
                f"Topic: {topic}, Q: {question[:100]}",
                outcome="success" if success else "failure",
                confidence=0.85,
                data={
                    "topic": topic,
                    "question": question[:200],
                    "answer_length": len(answer),
                    "source": "kimi_cloud",
                },
            )
        except Exception:
            pass

    def ask(
        self,
        question: str,
        topic: str = "general",
        code_files: Optional[List[str]] = None,
        max_tokens: int = 800,
    ) -> Dict[str, Any]:
        """
        Ask Kimi to teach Grace something.

        Every call creates a Genesis Key, compiles the response,
        stores in memory, and feeds Oracle ML.

        Args:
            question: What Grace wants to learn
            topic: Domain/topic for classification
            code_files: Source code files for context (read-only)
            max_tokens: Response length limit

        Returns:
            Teaching result with compiled knowledge
        """
        cloud = self._get_cloud()
        if not cloud or not cloud.is_available():
            return {"success": False, "error": "Kimi Cloud not available"}

        # Genesis Key for this interaction
        genesis_key_id = self._create_genesis_key(
            action=question[:200],
            details={"topic": topic, "code_files": code_files},
        )

        # Call Kimi Cloud
        if code_files:
            result = cloud.generate_with_code_context(
                prompt=question,
                code_files=code_files,
                max_tokens=max_tokens,
            )
        else:
            result = cloud.generate(prompt=question, max_tokens=max_tokens)

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Unknown")}

        answer = result["content"]
        tokens = result.get("tokens", 0)
        model = result.get("model_name", "kimi_cloud")

        # Store everywhere
        self._store_in_magma(question, answer, topic)
        compiled = self._compile_response(question, answer, topic, genesis_key_id)
        self._distill_response(question, answer, model)
        self._feed_oracle(question, answer, topic, True)

        self.session.commit()

        self._stats["total_lessons"] += 1
        self._stats["total_tokens"] += tokens
        if topic not in self._stats["topics_mined"]:
            self._stats["topics_mined"].append(topic)

        logger.info(
            f"[KIMI-TEACHER] Lesson on '{topic}': {tokens} tokens, "
            f"compiled {sum(len(v) for v in compiled.values() if isinstance(v, list))} items"
        )

        return {
            "success": True,
            "answer": answer,
            "tokens": tokens,
            "model": model,
            "genesis_key": genesis_key_id,
            "compiled": {
                "facts": len(compiled.get("facts", [])),
                "procedures": len(compiled.get("procedures", [])),
                "rules": len(compiled.get("rules", [])),
                "entities": len(compiled.get("entities", [])),
            },
            "stored_in": ["magma_memory", "distilled_knowledge", "knowledge_compiler", "oracle_ml"],
        }

    def mine_topic(
        self,
        topic: str,
        questions: Optional[List[str]] = None,
        max_questions: int = 5,
        max_tokens_per_question: int = 600,
    ) -> Dict[str, Any]:
        """
        Mine Kimi for knowledge on a topic.

        Asks multiple questions, compiles all answers.
        Grace learns a whole domain from one mining session.
        """
        if not questions:
            questions = [
                f"What is {topic}? Define it precisely.",
                f"What are the key concepts and principles of {topic}?",
                f"What are the best practices for {topic}?",
                f"What are common mistakes and pitfalls in {topic}?",
                f"What tools and frameworks are used in {topic}?",
                f"How do you measure success in {topic}?",
                f"What are the current trends in {topic}?",
            ]

        questions = questions[:max_questions]
        results = []
        total_tokens = 0
        total_compiled = {"facts": 0, "procedures": 0, "rules": 0, "entities": 0}

        for q in questions:
            result = self.ask(q, topic=topic, max_tokens=max_tokens_per_question)
            results.append(result)

            if result.get("success"):
                total_tokens += result.get("tokens", 0)
                for key in total_compiled:
                    total_compiled[key] += result.get("compiled", {}).get(key, 0)

        succeeded = sum(1 for r in results if r.get("success"))

        return {
            "topic": topic,
            "questions_asked": len(questions),
            "succeeded": succeeded,
            "total_tokens": total_tokens,
            "total_compiled": total_compiled,
            "stored_in": ["magma_memory", "distilled_knowledge", "knowledge_compiler", "oracle_ml"],
        }

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


_teacher: Optional[KimiTeacher] = None


def get_kimi_teacher(session: Session) -> KimiTeacher:
    global _teacher
    if _teacher is None:
        _teacher = KimiTeacher(session)
    return _teacher
