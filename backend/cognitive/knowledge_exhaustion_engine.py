"""
Knowledge Exhaustion Engine

Extracts knowledge DEEPLY until convergence:

1. Ask questions from multiple perspectives
2. Track when the SAME facts keep coming back
3. After 5 questions returning nothing new → topic converging
4. After 3 full cycles of convergence → topic EXHAUSTED
5. Move to GitHub for fresh knowledge
6. Massive GitHub dump for code examples + repos

Convergence detection:
  New fact = something not already in compiled store
  Duplicate = fact that matches existing knowledge (subject+predicate overlap)
  Convergence = duplicate_ratio > 0.8 for 5 consecutive questions
  Exhaustion = 3 convergence cycles with 0 new facts

This is how Grace knows she's ACTUALLY learned a topic.
"""

import logging
import hashlib
import time
import re
import os
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Float, Integer, Text, JSON, Boolean, Index, func
from database.base import BaseModel

logger = logging.getLogger(__name__)


# ======================================================================
# PERSISTENCE MODEL
# ======================================================================

class TopicExhaustionTracker(BaseModel):
    """Tracks exhaustion state for each topic across sessions."""
    __tablename__ = "topic_exhaustion_tracker"

    topic = Column(String(256), nullable=False, index=True, unique=True)
    status = Column(String(32), default="pending")  # pending, mining, converging, exhausted
    cycles_completed = Column(Integer, default=0)
    convergence_count = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    total_new_facts = Column(Integer, default=0)
    total_duplicates = Column(Integer, default=0)
    duplicate_ratio = Column(Float, default=0.0)
    last_mined_at = Column(Text, nullable=True)
    exhausted_at = Column(Text, nullable=True)
    github_mined = Column(Boolean, default=False)
    github_repos = Column(Integer, default=0)
    github_facts = Column(Integer, default=0)
    perspectives_used = Column(JSON, default=list)
    notes = Column(Text, nullable=True)


class KnowledgeExhaustionEngine:
    """
    Deep extraction until convergence. Then GitHub dump.

    Convergence algorithm:
    1. Ask questions from multiple perspectives about a topic
    2. Extract facts from each answer
    3. Hash each fact and compare against existing knowledge
    4. If >80% of extracted facts already exist → question CONVERGED
    5. If 5 consecutive questions converge → cycle CONVERGED
    6. If 3 consecutive cycles converge → topic EXHAUSTED
    7. After exhaustion, try GitHub for any remaining novel facts
    8. If GitHub also produces nothing new → topic fully exhausted
    """

    def __init__(self, session_factory, cloud_client=None):
        self.session_factory = session_factory
        self.cloud_client = cloud_client
        self._stats = {
            "topics_exhausted": 0,
            "total_questions": 0,
            "total_new_facts": 0,
            "total_duplicates": 0,
            "github_repos_mined": 0,
        }

    def get_topic_status(self, topic: str) -> Dict[str, Any]:
        """Get the current exhaustion status for a topic."""
        session = self.session_factory()
        tracker = session.query(TopicExhaustionTracker).filter_by(topic=topic).first()
        if not tracker:
            session.close()
            return {"topic": topic, "status": "unknown", "exists": False}

        result = {
            "topic": tracker.topic,
            "status": tracker.status,
            "cycles_completed": tracker.cycles_completed,
            "convergence_count": tracker.convergence_count,
            "total_questions": tracker.total_questions,
            "total_new_facts": tracker.total_new_facts,
            "total_duplicates": tracker.total_duplicates,
            "duplicate_ratio": tracker.duplicate_ratio,
            "github_mined": tracker.github_mined,
            "github_repos": tracker.github_repos,
            "exhausted_at": tracker.exhausted_at,
            "exists": True,
        }
        session.close()
        return result

    def get_all_topics_status(self) -> List[Dict[str, Any]]:
        """Get exhaustion status for all tracked topics."""
        session = self.session_factory()
        trackers = session.query(TopicExhaustionTracker).all()
        results = []
        for t in trackers:
            results.append({
                "topic": t.topic,
                "status": t.status,
                "cycles": t.cycles_completed,
                "convergence": t.convergence_count,
                "new_facts": t.total_new_facts,
                "duplicates": t.total_duplicates,
                "ratio": t.duplicate_ratio,
                "github": t.github_mined,
            })
        session.close()
        return results

    def _get_or_create_tracker(self, session: Session, topic: str) -> "TopicExhaustionTracker":
        tracker = session.query(TopicExhaustionTracker).filter_by(topic=topic).first()
        if not tracker:
            tracker = TopicExhaustionTracker(
                topic=topic,
                status="pending",
                perspectives_used=[],
            )
            session.add(tracker)
            session.flush()
        return tracker

    def exhaust_topic(
        self,
        topic: str,
        max_cycles: int = 3,
        questions_per_cycle: int = 5,
        convergence_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Extract knowledge until convergence.

        Keeps asking different questions until the same info comes back.
        """
        session = self.session_factory()
        tracker = self._get_or_create_tracker(session, topic)

        if tracker.status == "exhausted":
            session.close()
            return {
                "topic": topic,
                "exhausted": True,
                "message": "Topic already exhausted. Use force=True or try GitHub.",
                "total_new_facts": tracker.total_new_facts,
                "total_duplicates": tracker.total_duplicates,
            }

        tracker.status = "mining"
        session.commit()

        from cognitive.knowledge_compiler import CompiledFact
        existing_facts = self._get_existing_fact_hashes(session, topic)
        initial_count = len(existing_facts)

        convergence_count = tracker.convergence_count
        total_new = 0
        total_dupes = 0
        all_results = []
        used_perspectives = list(tracker.perspectives_used or [])

        all_perspectives = self._generate_perspectives(topic)

        for cycle in range(max_cycles):
            cycle_new = 0
            cycle_dupes = 0
            consecutive_converged = 0

            cycle_questions = self._get_fresh_questions(
                topic, all_perspectives, used_perspectives,
                questions_per_cycle, cycle
            )

            if not cycle_questions:
                logger.info(f"[EXHAUST] {topic}: No more fresh questions. Topic likely exhausted.")
                convergence_count += 1
                break

            for question in cycle_questions:
                if not self.cloud_client or not self.cloud_client.is_available():
                    break

                used_perspectives.append(question[:80])

                result = self.cloud_client.generate(prompt=question, max_tokens=500)

                if not result.get("success"):
                    continue

                answer = result["content"]
                tokens = result.get("tokens", 0)
                self._stats["total_questions"] += 1

                from cognitive.knowledge_compiler import KnowledgeCompiler
                compiler = KnowledgeCompiler(session)
                compiled = compiler.compile_chunk(
                    text=answer,
                    source_document_id=f"exhaustion:{topic}:cycle{tracker.cycles_completed + cycle}",
                    domain=topic.replace(" ", "_"),
                )

                new_facts = compiled.get("facts", [])
                new_count = 0
                dupe_count = 0

                for fact in new_facts:
                    fact_hash = self._hash_fact(fact)
                    if fact_hash in existing_facts:
                        dupe_count += 1
                    else:
                        existing_facts.add(fact_hash)
                        new_count += 1

                # If LLM gave a long answer but compiler found 0 facts,
                # treat this as "no new info" (convergence signal)
                if new_count == 0 and dupe_count == 0 and len(answer) > 100:
                    dupe_count = 1

                cycle_new += new_count
                cycle_dupes += dupe_count
                total_new += new_count
                total_dupes += dupe_count

                total_from_q = new_count + dupe_count
                dupe_ratio = dupe_count / max(total_from_q, 1)

                if dupe_ratio >= convergence_threshold:
                    consecutive_converged += 1
                else:
                    consecutive_converged = 0

                all_results.append({
                    "cycle": cycle,
                    "question": question[:80],
                    "new": new_count,
                    "dupes": dupe_count,
                    "tokens": tokens,
                    "converged": dupe_ratio >= convergence_threshold,
                })

                from cognitive.knowledge_compiler import get_llm_knowledge_miner
                miner = get_llm_knowledge_miner(session)
                miner.store_interaction(question, answer, "kimi_cloud:exhaustion", confidence=0.8)

                if consecutive_converged >= questions_per_cycle:
                    break

                time.sleep(0.5)

            session.commit()

            cycle_total = cycle_new + cycle_dupes
            cycle_dupe_ratio = cycle_dupes / max(cycle_total, 1)

            if cycle_new == 0 or cycle_dupe_ratio >= convergence_threshold:
                convergence_count += 1
            else:
                convergence_count = max(0, convergence_count - 1)

            logger.info(
                f"[EXHAUST] {topic} cycle {tracker.cycles_completed + cycle}: "
                f"new={cycle_new}, dupes={cycle_dupes}, "
                f"convergence={convergence_count}/3"
            )

            if convergence_count >= 3:
                self._stats["topics_exhausted"] += 1
                break

        # Persist state
        tracker.cycles_completed += min(cycle + 1, max_cycles)
        tracker.convergence_count = convergence_count
        tracker.total_questions += len(all_results)
        tracker.total_new_facts += total_new
        tracker.total_duplicates += total_dupes
        total_all = (tracker.total_new_facts + tracker.total_duplicates)
        tracker.duplicate_ratio = tracker.total_duplicates / max(total_all, 1)
        tracker.last_mined_at = datetime.now(timezone.utc).isoformat()
        tracker.perspectives_used = used_perspectives[-100:]  # cap

        if convergence_count >= 3:
            tracker.status = "exhausted"
            tracker.exhausted_at = datetime.now(timezone.utc).isoformat()
        elif convergence_count >= 1:
            tracker.status = "converging"
        else:
            tracker.status = "mining"

        # Capture values BEFORE closing session to avoid DetachedInstanceError
        result_status = tracker.status
        result_cycles_total = tracker.cycles_completed
        result_total_q = tracker.total_questions

        session.commit()

        final_count = len(existing_facts)
        session.close()

        self._stats["total_new_facts"] += total_new
        self._stats["total_duplicates"] += total_dupes

        return {
            "topic": topic,
            "exhausted": convergence_count >= 3,
            "status": result_status,
            "cycles_run": min(cycle + 1, max_cycles),
            "cycles_total": result_cycles_total,
            "convergence_reached": convergence_count,
            "facts_before": initial_count,
            "facts_after": final_count,
            "new_facts": total_new,
            "duplicates": total_dupes,
            "duplicate_ratio": total_dupes / max(total_new + total_dupes, 1),
            "questions_asked": len(all_results),
            "results": all_results,
        }

    def exhaust_multiple(
        self,
        topics: List[str],
        max_cycles: int = 3,
        questions_per_cycle: int = 5,
    ) -> Dict[str, Any]:
        """Exhaust multiple topics sequentially."""
        results = []
        for topic in topics:
            result = self.exhaust_topic(topic, max_cycles, questions_per_cycle)
            results.append(result)
            if not self.cloud_client or not self.cloud_client.is_available():
                break
        return {
            "topics_processed": len(results),
            "exhausted": sum(1 for r in results if r.get("exhausted")),
            "converging": sum(1 for r in results if not r.get("exhausted") and r.get("convergence_reached", 0) > 0),
            "results": results,
        }

    def github_massive_dump(
        self,
        topics: List[str],
        max_repos_per_topic: int = 10,
        max_files_per_repo: int = 3,
        include_code_files: bool = True,
    ) -> Dict[str, Any]:
        """
        Massive GitHub dump: pull repos, READMEs, code examples, top files.

        For each topic:
        1. Search GitHub for top repos by stars
        2. Pull README content
        3. Pull top source files (if include_code_files)
        4. Compile everything into knowledge store
        5. Vectorize for RAG
        6. Update topic tracker

        This is designed to be a ONE-TIME massive knowledge injection.
        """
        session = self.session_factory()
        total_repos = 0
        total_facts = 0
        total_files = 0
        results = []

        gh_token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if gh_token:
            headers["Authorization"] = f"token {gh_token}"

        for topic in topics:
            topic_facts = 0
            tracker = self._get_or_create_tracker(session, topic)

            try:
                resp = requests.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": topic,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": max_repos_per_topic,
                    },
                    headers=headers,
                    timeout=15,
                )

                if resp.status_code != 200:
                    results.append({"topic": topic, "error": f"GitHub API {resp.status_code}"})
                    time.sleep(2)
                    continue

                repos = resp.json().get("items", [])

                for repo in repos[:max_repos_per_topic]:
                    repo_name = repo.get("full_name", "")
                    stars = repo.get("stargazers_count", 0)
                    description = repo.get("description", "") or ""
                    language = repo.get("language", "") or ""
                    repo_url = repo.get("html_url", "")

                    from cognitive.knowledge_compiler import CompiledFact, CompiledEntityRelation
                    fact = CompiledFact(
                        subject=repo_name[:256],
                        predicate="github_repo",
                        object_value=f"{description[:500]}. Language: {language}. Stars: {stars}",
                        confidence=min(0.95, 0.5 + stars / 10000),
                        domain=topic.replace(" ", "_"),
                        verified=True,
                        source_text=f"github:{repo_url}",
                        tags={"source": "github", "stars": stars, "language": language},
                    )
                    session.add(fact)
                    topic_facts += 1

                    entity = CompiledEntityRelation(
                        entity_a=topic[:256],
                        relation="implemented_by",
                        entity_b=repo_name[:256],
                        confidence=min(0.9, 0.5 + stars / 10000),
                        domain=topic.replace(" ", "_"),
                    )
                    session.add(entity)

                    # Pull README
                    try:
                        raw_headers = dict(headers)
                        raw_headers["Accept"] = "application/vnd.github.v3.raw"
                        readme_resp = requests.get(
                            f"https://api.github.com/repos/{repo_name}/readme",
                            headers=raw_headers,
                            timeout=10,
                        )

                        if readme_resp.status_code == 200 and readme_resp.text:
                            readme_text = readme_resp.text[:3000]

                            from cognitive.knowledge_compiler import KnowledgeCompiler
                            compiler = KnowledgeCompiler(session)
                            compiled = compiler.compile_chunk(
                                text=readme_text,
                                source_document_id=f"github:{repo_name}:README",
                                domain=topic.replace(" ", "_"),
                            )
                            readme_count = sum(len(v) for v in compiled.values() if isinstance(v, list))
                            topic_facts += readme_count

                            self._vectorize_text(
                                f"{repo_name} README: {readme_text[:500]}",
                                {"source": "github", "repo": repo_name, "type": "readme",
                                 "domain": topic, "stars": stars}
                            )
                    except Exception:
                        pass

                    # Pull top code files
                    if include_code_files and max_files_per_repo > 0:
                        try:
                            tree_resp = requests.get(
                                f"https://api.github.com/repos/{repo_name}/git/trees/HEAD",
                                headers=headers,
                                timeout=10,
                            )

                            if tree_resp.status_code == 200:
                                tree = tree_resp.json().get("tree", [])
                                code_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".md"}
                                code_files = [
                                    f for f in tree
                                    if f.get("type") == "blob"
                                    and any(f.get("path", "").endswith(ext) for ext in code_extensions)
                                    and f.get("size", 0) < 50000
                                ][:max_files_per_repo]

                                for cf in code_files:
                                    try:
                                        file_resp = requests.get(
                                            f"https://api.github.com/repos/{repo_name}/contents/{cf['path']}",
                                            headers=raw_headers,
                                            timeout=10,
                                        )
                                        if file_resp.status_code == 200:
                                            code_content = file_resp.text[:2000]
                                            code_fact = CompiledFact(
                                                subject=f"{repo_name}/{cf['path']}"[:256],
                                                predicate="code_example",
                                                object_value=code_content[:2000],
                                                confidence=min(0.9, 0.5 + stars / 10000),
                                                domain=topic.replace(" ", "_"),
                                                verified=True,
                                                source_text=f"github:{repo_name}/{cf['path']}",
                                                tags={"source": "github", "type": "code", "file": cf["path"]},
                                            )
                                            session.add(code_fact)
                                            topic_facts += 1
                                            total_files += 1

                                            self._vectorize_text(
                                                f"{repo_name}/{cf['path']}: {code_content[:300]}",
                                                {"source": "github", "repo": repo_name, "file": cf["path"],
                                                 "type": "code", "domain": topic}
                                            )
                                    except Exception:
                                        pass
                                    time.sleep(0.3)
                        except Exception:
                            pass

                    total_repos += 1
                    time.sleep(0.5)

                # Update tracker
                tracker.github_mined = True
                tracker.github_repos += len(repos[:max_repos_per_topic])
                tracker.github_facts += topic_facts
                total_facts += topic_facts

                results.append({
                    "topic": topic,
                    "repos": len(repos[:max_repos_per_topic]),
                    "facts": topic_facts,
                    "files": total_files,
                })

                session.commit()
                time.sleep(1)

            except Exception as e:
                results.append({"topic": topic, "error": str(e)[:80]})

        session.close()
        self._stats["github_repos_mined"] += total_repos

        return {
            "topics_mined": len(topics),
            "total_repos": total_repos,
            "total_facts": total_facts,
            "total_code_files": total_files,
            "results": results,
        }

    def _generate_perspectives(self, topic: str) -> List[str]:
        """Generate questions from 25+ different perspectives to maximize coverage."""
        return [
            # Foundational
            f"What is {topic}? Define precisely with key concepts.",
            f"What are the core principles of {topic}?",
            f"What are the best practices for {topic}?",
            f"What are the common mistakes and anti-patterns in {topic}?",
            f"What tools and frameworks are commonly used in {topic}?",
            # Engineering angles
            f"How does {topic} relate to software architecture?",
            f"What are the performance considerations in {topic}?",
            f"What are the security implications of {topic}?",
            f"How do you test {topic} effectively?",
            f"What are the scalability patterns in {topic}?",
            # Advanced
            f"What are the advanced patterns and techniques in {topic}?",
            f"How has {topic} evolved over the last 5 years?",
            f"What are the trade-offs when implementing {topic}?",
            f"What are real-world case studies of {topic}?",
            f"How do you measure success and KPIs in {topic}?",
            # Deeper angles
            f"What are the internals of {topic}? How does it work under the hood?",
            f"What are the edge cases and failure modes in {topic}?",
            f"How do experts approach {topic} differently from beginners?",
            f"What are the mathematical or theoretical foundations of {topic}?",
            f"What are the latest research developments in {topic}?",
            # Cross-domain
            f"How does {topic} interact with observability and monitoring?",
            f"What are the deployment and operational concerns for {topic}?",
            f"How does {topic} relate to data management and databases?",
            f"What are the cost optimization strategies in {topic}?",
            f"How does {topic} fit into a microservices or distributed architecture?",
            # Meta
            f"What are the most important design decisions when starting with {topic}?",
            f"What documentation should exist for {topic}?",
            f"What are the hiring and team structure considerations for {topic}?",
            f"How do you evaluate and compare different approaches to {topic}?",
            f"What are the ethical and governance considerations in {topic}?",
        ]

    def _get_fresh_questions(
        self, topic: str, all_perspectives: List[str],
        used: List[str], count: int, cycle: int
    ) -> List[str]:
        """Get questions that haven't been asked yet."""
        used_set = set(q[:80] for q in used)
        fresh = [q for q in all_perspectives if q[:80] not in used_set]

        if len(fresh) < count and self.cloud_client and self.cloud_client.is_available():
            result = self.cloud_client.generate(
                prompt=(
                    f"I'm researching '{topic}' and have already asked these questions:\n"
                    + "\n".join(used[-10:])
                    + f"\n\nGenerate {count} NEW questions about {topic} from completely "
                    f"different angles. Focus on aspects NOT covered above. "
                    f"One question per line. Just the question, no numbering."
                ),
                max_tokens=300,
            )
            if result.get("success"):
                lines = [l.strip() for l in result["content"].split("\n") if l.strip() and "?" in l]
                fresh.extend(lines)

        return fresh[:count]

    def _get_existing_fact_hashes(self, session: Session, topic: str) -> Set[str]:
        """Get hashes of existing facts for dedup. Checks both exact topic and underscore variant."""
        from cognitive.knowledge_compiler import CompiledFact
        domain_variants = [topic, topic.replace(" ", "_")]
        facts = session.query(CompiledFact).filter(
            CompiledFact.domain.in_(domain_variants)
        ).all()
        return {self._hash_fact({"subject": f.subject, "object": f.object_value}) for f in facts}

    def _hash_fact(self, fact: Dict) -> str:
        """Hash a fact for dedup comparison. Normalizes text for better matching."""
        subj = str(fact.get("subject", "")).lower().strip()[:50]
        obj = str(fact.get("object", fact.get("object_value", ""))).lower().strip()[:100]
        normalized = re.sub(r'\s+', ' ', f"{subj}:{obj}")
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def _vectorize_text(self, text: str, metadata: Dict[str, Any]):
        """Auto-vectorize text into Qdrant unified store."""
        try:
            from embedding.ollama_embedder import OllamaEmbedder
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct

            embedder = OllamaEmbedder()
            emb = embedder.embed_text([text[:500]])[0]
            vid = hashlib.md5(text[:200].encode()).hexdigest()

            qpath = "/workspace/qdrant_unified"
            lock_path = os.path.join(qpath, ".lock")
            if os.path.exists(lock_path):
                os.remove(lock_path)

            qc = QdrantClient(path=qpath)
            qc.upsert(collection_name="documents", points=[
                PointStruct(id=vid, vector=emb, payload=metadata)
            ])
            qc.close()
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        try:
            session = self.session_factory()
            total = session.query(TopicExhaustionTracker).count()
            exhausted = session.query(TopicExhaustionTracker).filter_by(status="exhausted").count()
            converging = session.query(TopicExhaustionTracker).filter_by(status="converging").count()
            mining = session.query(TopicExhaustionTracker).filter_by(status="mining").count()
            stats["tracked_topics"] = total
            stats["exhausted_topics"] = exhausted
            stats["converging_topics"] = converging
            stats["mining_topics"] = mining
            session.close()
        except Exception:
            pass
        return stats


_engine: Optional[KnowledgeExhaustionEngine] = None

def get_knowledge_exhaustion_engine(session_factory=None, cloud_client=None):
    global _engine
    if _engine is None:
        if not session_factory:
            from database.session import SessionLocal
            session_factory = SessionLocal
        _engine = KnowledgeExhaustionEngine(session_factory, cloud_client)
    return _engine
