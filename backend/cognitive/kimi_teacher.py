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
        self._system_context_cache: Optional[str] = None

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

    def _gather_system_context(self) -> str:
        """
        Read ALL Grace system states (read-only) to give Kimi Cloud
        full context when teaching. Cached per session.
        """
        if self._system_context_cache:
            return self._system_context_cache

        context_parts = []

        # GraceBrain state
        try:
            from cognitive.grace_brain import GraceBrain
            brain = GraceBrain(self.session)
            state = brain.read_system_state()
            for key, value in state.items():
                if key == "timestamp":
                    continue
                if isinstance(value, dict):
                    connected = value.get("connected", "N/A")
                    context_parts.append(f"{key}: connected={connected}")
                    for k, v in value.items():
                        if k not in ("connected", "error") and v and str(v) != "False":
                            context_parts.append(f"  {k}={v}")
        except Exception:
            pass

        # Diagnostic health
        try:
            from cognitive.system_integrity_monitor import get_system_integrity_monitor
            monitor = get_system_integrity_monitor(self.session)
            report = monitor.get_quick_status()
            context_parts.append(f"integrity: health={report.get('health_score', '?')}, issues={report.get('total_issues', '?')}")
        except Exception:
            pass

        # Knowledge store stats
        try:
            from cognitive.knowledge_compiler import CompiledFact, CompiledProcedure, CompiledDecisionRule, DistilledKnowledge
            context_parts.append(f"knowledge_store: facts={self.session.query(CompiledFact).count()}, procedures={self.session.query(CompiledProcedure).count()}, rules={self.session.query(CompiledDecisionRule).count()}")
            context_parts.append(f"distilled_knowledge: {self.session.query(DistilledKnowledge).count()} entries")
        except Exception:
            pass

        # Weight system
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            ws = get_grace_weight_system(self.session)
            stats = ws.get_stats()
            context_parts.append(f"weights: updates={stats.get('total_weight_updates', 0)}, kpis={stats.get('current_kpis', {})}")
        except Exception:
            pass

        # Task stats
        try:
            from cognitive.task_completion_verifier import VerifiedTask
            total = self.session.query(VerifiedTask).count()
            complete = self.session.query(VerifiedTask).filter(VerifiedTask.status == "complete").count()
            context_parts.append(f"tasks: total={total}, complete={complete}")
        except Exception:
            pass

        # Feedback loop recommendations
        try:
            from cognitive.feedback_loops import get_feedback_coordinator
            coord = get_feedback_coordinator(self.session)
            recs = coord.get_recommendations()
            gaps = recs.get("knowledge_gaps", [])[:3]
            if gaps:
                context_parts.append(f"knowledge_gaps: {[g.get('topic', '?') for g in gaps]}")
        except Exception:
            pass

        context = "\n".join(context_parts)
        self._system_context_cache = context[:2000]  # Cap for cost
        return self._system_context_cache

    def ask_with_system_context(
        self,
        question: str,
        topic: str = "general",
        code_files: Optional[List[str]] = None,
        max_tokens: int = 800,
    ) -> Dict[str, Any]:
        """
        Ask Kimi with FULL system state context.

        Kimi sees diagnostics, health, knowledge gaps, weights, tasks --
        everything Grace knows about herself. Read-only.
        """
        system_context = self._gather_system_context()
        enriched_question = f"Grace System State:\n{system_context}\n\nQuestion: {question}"
        return self.ask(enriched_question, topic=topic, code_files=code_files, max_tokens=max_tokens)

    def audit_and_teach(self, max_tokens: int = 600) -> Dict[str, Any]:
        """
        Kimi reads Grace's full state and teaches her what needs fixing.

        This is the key learning loop: Kimi audits, identifies gaps,
        teaches Grace about those gaps, Grace stores the knowledge.
        """
        system_context = self._gather_system_context()

        audit_question = f"""You are auditing Grace OS. Here is the current system state:

{system_context}

Based on this state:
1. What are the top 3 issues that need attention?
2. What knowledge gaps should be filled first?
3. What integrations are missing or broken?
4. What would improve the system most right now?

Be specific. Reference actual numbers from the state data."""

        return self.ask(audit_question, topic="grace_audit", max_tokens=max_tokens)

    def learn_from_diagnostics(self, max_tokens: int = 500) -> Dict[str, Any]:
        """Ask Kimi to analyze diagnostic data and teach Grace what it means."""
        system_context = self._gather_system_context()
        return self.ask(
            f"Analyze this diagnostic data and explain what needs healing:\n{system_context}",
            topic="diagnostics",
            max_tokens=max_tokens,
        )

    def learn_domain(
        self,
        domain: str,
        depth: str = "overview",
        max_questions: int = 5,
    ) -> Dict[str, Any]:
        """
        Comprehensive domain learning. Uses Kimi to teach Grace
        a whole domain from scratch.

        depth: 'overview' (3 questions), 'intermediate' (5), 'deep' (7)
        """
        question_sets = {
            "overview": [
                f"What is {domain}? Define the key concepts in 3-4 sentences.",
                f"What are the essential best practices for {domain}?",
                f"What tools and frameworks are most important in {domain}?",
            ],
            "intermediate": [
                f"What is {domain}? Define the key concepts.",
                f"What are the essential best practices for {domain}?",
                f"What are the common mistakes and anti-patterns in {domain}?",
                f"What tools, frameworks, and technologies are used in {domain}?",
                f"How do you measure success and quality in {domain}?",
            ],
            "deep": [
                f"What is {domain}? Define all key concepts and principles.",
                f"What are the best practices and design patterns for {domain}?",
                f"What are the common mistakes, anti-patterns, and pitfalls in {domain}?",
                f"What tools, frameworks, and technologies are used in {domain}?",
                f"How do you measure success, quality, and performance in {domain}?",
                f"What are the current trends and future directions in {domain}?",
                f"How does {domain} integrate with other engineering practices?",
            ],
        }

        questions = question_sets.get(depth, question_sets["overview"])[:max_questions]
        return self.mine_topic(domain, questions=questions, max_questions=max_questions)

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

        try:
            from cognitive.timesense import get_timesense
            get_timesense().record_operation("kimi.teach", tokens, "kimi_teacher")
        except Exception:
            pass
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

    def verify_with_cloud(self, content: str, original_query: str) -> Dict[str, Any]:
        """Use Kimi Cloud as adversarial checker (hallucination guard Layer 11)."""
        cloud = self._get_cloud()
        if not cloud or not cloud.is_available():
            return {"verified": None, "reason": "cloud unavailable"}

        result = cloud.generate(
            prompt=f"Fact-check this response. List ONLY errors. If accurate, say 'NO ERRORS'.\n\nQuestion: {original_query[:200]}\nResponse to check:\n{content[:1000]}",
            system_prompt="You are a strict fact-checker. Only flag genuine errors.",
            max_tokens=300,
        )

        if result.get("success"):
            answer = result["content"].lower()
            verified = "no errors" in answer
            self._feed_oracle(original_query, content, "verification", verified)
            return {"verified": verified, "response": result["content"], "tokens": result.get("tokens", 0)}
        return {"verified": None, "reason": result.get("error", "unknown")}

    def extract_knowledge_from_file(self, file_path: str, max_chunks: int = 3) -> Dict[str, Any]:
        """Send document chunks to Kimi Cloud for high-quality extraction."""
        cloud = self._get_cloud()
        if not cloud or not cloud.is_available():
            return {"success": False, "error": "cloud unavailable"}

        import os, re
        full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), file_path)
        if not os.path.exists(full_path):
            return {"success": False, "error": f"file not found: {file_path}"}

        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        chunks = [p.strip() for p in re.split(r'\n\n+', content) if len(p.strip()) > 100][:max_chunks]
        total_compiled = {"facts": 0, "procedures": 0, "rules": 0, "entities": 0}

        for chunk in chunks:
            result = self.ask(
                f"Extract all facts, procedures, and rules from this text:\n{chunk[:1500]}",
                topic=os.path.basename(os.path.dirname(file_path)),
                max_tokens=500,
            )
            if result.get("success"):
                for k in total_compiled:
                    total_compiled[k] += result.get("compiled", {}).get(k, 0)

        return {"success": True, "file": file_path, "chunks_processed": len(chunks), "compiled": total_compiled}

    def get_task_breakdown(self, task_description: str) -> Dict[str, Any]:
        """Ask Kimi Cloud to break down a complex task."""
        return self.ask(
            f"Break down this task into ordered steps with dependencies. "
            f"For each step: action, depends_on (which previous steps), estimated_minutes.\n\n"
            f"Task: {task_description}",
            topic="task_management",
            max_tokens=600,
        )

    def review_code(self, file_path: str) -> Dict[str, Any]:
        """Send code to Kimi Cloud for review."""
        cloud = self._get_cloud()
        if not cloud:
            return {"success": False, "error": "cloud unavailable"}

        result = cloud.generate_with_code_context(
            prompt="Review this code for: bugs, security issues, performance problems, and improvements. Be specific with line references.",
            code_files=[file_path],
            max_tokens=600,
        )

        if result.get("success"):
            self._compile_response(f"Code review: {file_path}", result["content"], "code_review", None)
            self._distill_response(f"review:{file_path}", result["content"], result.get("model_name", "kimi_cloud"))
            self.session.commit()

        return {"success": result.get("success", False), "review": result.get("content", ""), "tokens": result.get("tokens", 0)}

    def mine_knowledge_gaps(self) -> Dict[str, Any]:
        """Read knowledge gaps from feedback loops, auto-mine each from cloud."""
        try:
            from cognitive.feedback_loops import get_feedback_coordinator
            coord = get_feedback_coordinator(self.session)
            recs = coord.get_recommendations()
            gaps = recs.get("knowledge_gaps", [])[:5]
        except Exception:
            gaps = []

        if not gaps:
            return {"mined": 0, "message": "No knowledge gaps detected"}

        results = []
        for gap in gaps:
            topic = gap.get("topic", "unknown")
            result = self.ask(
                f"Teach me about {topic}. What are the key concepts, best practices, and common patterns?",
                topic=topic,
                max_tokens=500,
            )
            results.append({"topic": topic, "success": result.get("success", False), "tokens": result.get("tokens", 0)})

        return {"mined": len(results), "gaps_addressed": results}

    def compose_for_unified_chain(self, query: str, facts: List[Dict]) -> Optional[str]:
        """High-quality composition for unified intelligence chain."""
        cloud = self._get_cloud()
        if not cloud or not cloud.is_available():
            return None

        fact_text = "\n".join(f"- {f.get('subject', '')} {f.get('predicate', '')} {f.get('object', f.get('object_value', ''))}" for f in facts[:8])

        result = cloud.generate(
            prompt=f"Based on these facts, compose a clear answer to: {query}\n\nFacts:\n{fact_text}",
            system_prompt="Compose a concise answer using ONLY the facts provided. Don't add information not in the facts.",
            max_tokens=400,
        )

        if result.get("success"):
            answer = result["content"]
            self._distill_response(query, answer, "kimi_cloud:composer")
            self.session.commit()
            return answer

        return None

    def mine_chat_history(self, limit: int = 20) -> Dict[str, Any]:
        """Mine past conversations for patterns via cloud extraction."""
        try:
            from models.database_models import Chat
            chats = self.session.query(Chat).order_by(Chat.created_at.desc()).limit(limit).all()
        except Exception:
            chats = []

        if not chats:
            return {"mined": 0, "message": "No chat history found"}

        mined = 0
        for chat in chats:
            user_msg = getattr(chat, 'user_message', '') or ''
            assistant_msg = getattr(chat, 'assistant_message', '') or getattr(chat, 'response', '') or ''
            if user_msg and assistant_msg and len(user_msg) > 20:
                self._distill_response(user_msg, assistant_msg, "chat_history")
                mined += 1

        self.session.commit()
        return {"mined": mined, "source": "chat_history"}

    def mine_git_patterns(self) -> Dict[str, Any]:
        """Mine git commit patterns for code quality learning."""
        import subprocess
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-50'],
                capture_output=True, text=True, timeout=10,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            commits = result.stdout.strip().split('\n') if result.stdout else []
        except Exception:
            commits = []

        if not commits:
            return {"mined": 0, "message": "No git history"}

        commit_text = "\n".join(commits[:30])
        result = self.ask(
            f"Analyze these git commits and extract: coding patterns, common change types, quality indicators:\n{commit_text}",
            topic="code_patterns",
            max_tokens=400,
        )
        return {"mined": 1 if result.get("success") else 0, "commits_analyzed": len(commits)}

    def correct_response(self, query: str, wrong_answer: str, correct_info: str) -> Dict[str, Any]:
        """User corrects a cloud response. Downweight wrong, store correct."""
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            miner = get_llm_knowledge_miner(self.session)
            miner.update_quality(query, "negative")

            miner.store_interaction(
                query=query,
                response=correct_info,
                model_used="user_correction",
                confidence=0.95,
            )
            self.session.commit()
            return {"corrected": True, "query": query[:100]}
        except Exception as e:
            return {"corrected": False, "error": str(e)}

    def cross_reference_rag_and_compiled(self, query: str) -> Dict[str, Any]:
        """Cross-reference RAG results with compiled facts for reinforcement."""
        results = {"rag_hits": 0, "compiled_hits": 0, "reinforced": 0}

        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            import re
            terms = re.findall(r'\b[A-Z][a-z]+\b', query)[:3]
            compiled_facts = []
            for term in terms:
                compiled_facts.extend(compiler.query_facts(subject=term, limit=3))
            results["compiled_hits"] = len(compiled_facts)

            if compiled_facts:
                for fact in compiled_facts:
                    fact_obj = self.session.query(
                        __import__('cognitive.knowledge_compiler', fromlist=['CompiledFact']).CompiledFact
                    ).filter_by(id=fact.get("id")).first() if "id" in fact else None

                    if fact_obj:
                        fact_obj.confidence = min(1.0, (fact_obj.confidence or 0.5) + 0.02)
                        results["reinforced"] += 1

                self.session.commit()
        except Exception:
            pass

        return results

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


_teacher: Optional[KimiTeacher] = None


def get_kimi_teacher(session: Session) -> KimiTeacher:
    global _teacher
    if _teacher is None:
        _teacher = KimiTeacher(session)
    return _teacher
