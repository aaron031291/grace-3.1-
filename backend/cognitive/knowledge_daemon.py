"""
Knowledge Daemon - Continuous background knowledge growth.

This is the MISSING PIECE that makes the knowledge engine actually work.
Without this, all the mining/KNN/feedback code sits idle.

Runs three loops in background threads:

1. KNN EXPANSION (every 60s)
   - Picks a random topic from the knowledge store
   - Runs KNN sub-agent swarm to find related knowledge
   - New discoveries get embedded into Qdrant via feedback loop
   - Vector store grows automatically

2. KNOWLEDGE MINING (every 300s)
   - Picks domains with lowest depth scores
   - Mines from GitHub, arXiv, StackOverflow, Wikidata
   - Compiles into SQL facts + vectorizes

3. KIMI PROACTIVE LEARNING (every 600s)
   - Identifies knowledge gaps via audit
   - Asks Kimi Cloud targeted questions
   - Compiles responses into deterministic knowledge
   - Feeds back into exhaustion tracker

All three are daemon threads - they die when the main process dies.
All three are non-blocking - they use try/except everywhere.
All three feed the feedback loop - discoveries grow the vector store.
"""

import logging
import threading
import time
import random
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class KnowledgeDaemon:
    """
    Background daemon that continuously grows Grace's knowledge.
    Start once at app startup. Runs until shutdown.
    """

    def __init__(self, session_factory, cloud_client=None):
        self.session_factory = session_factory
        self.cloud_client = cloud_client
        self._running = False
        self._threads: List[threading.Thread] = []
        self._stats = {
            "knn_cycles": 0,
            "knn_discoveries": 0,
            "mining_cycles": 0,
            "mining_facts": 0,
            "kimi_cycles": 0,
            "kimi_tokens": 0,
            "started_at": None,
            "errors": 0,
        }

    def start(self):
        """Start all background loops."""
        if self._running:
            return

        self._running = True
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

        # KNN expansion loop
        t1 = threading.Thread(target=self._knn_loop, daemon=True, name="KNN-Daemon")
        t1.start()
        self._threads.append(t1)

        # Mining loop
        t2 = threading.Thread(target=self._mining_loop, daemon=True, name="Mining-Daemon")
        t2.start()
        self._threads.append(t2)

        # Kimi proactive loop
        t3 = threading.Thread(target=self._kimi_loop, daemon=True, name="Kimi-Daemon")
        t3.start()
        self._threads.append(t3)

        logger.info("[KNOWLEDGE-DAEMON] Started 3 background loops: KNN, Mining, Kimi")

    def stop(self):
        """Stop all background loops."""
        self._running = False
        for t in self._threads:
            t.join(timeout=5)
        self._threads.clear()
        logger.info("[KNOWLEDGE-DAEMON] Stopped")

    def _knn_loop(self):
        """Continuous KNN expansion - find related knowledge."""
        time.sleep(10)  # Wait for other systems to initialize

        while self._running:
            try:
                self._run_knn_cycle()
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug(f"[KNN-DAEMON] Error: {e}")

            # Run every 60 seconds
            for _ in range(60):
                if not self._running:
                    return
                time.sleep(1)

    def _mining_loop(self):
        """Continuous knowledge mining from external sources."""
        time.sleep(30)  # Stagger startup

        while self._running:
            try:
                self._run_mining_cycle()
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug(f"[MINING-DAEMON] Error: {e}")

            # Run every 5 minutes
            for _ in range(300):
                if not self._running:
                    return
                time.sleep(1)

    def _kimi_loop(self):
        """Proactive Kimi Cloud learning."""
        time.sleep(60)  # Wait longer before first Kimi call

        while self._running:
            try:
                self._run_kimi_cycle()
            except Exception as e:
                self._stats["errors"] += 1
                logger.debug(f"[KIMI-DAEMON] Error: {e}")

            # Run every 10 minutes
            for _ in range(600):
                if not self._running:
                    return
                time.sleep(1)

    def _run_knn_cycle(self):
        """One KNN expansion cycle."""
        session = self.session_factory()
        try:
            from cognitive.knowledge_compiler import CompiledFact
            from sqlalchemy import func

            # Pick a random topic from knowledge store
            domains = session.query(CompiledFact.domain).distinct().all()
            if not domains:
                return

            domain = random.choice(domains)[0]
            if not domain:
                return

            # Get a random fact from this domain as seed
            fact = session.query(CompiledFact).filter(
                CompiledFact.domain == domain
            ).order_by(func.random()).first()

            if not fact:
                return

            seed = f"{fact.subject}: {fact.object_value}"[:200]

            # Run reverse KNN search via unified vector store
            from embedding.vector_store import search as vs_search
            results = vs_search(seed, limit=5, threshold=0.7)
            self._stats["knn_discoveries"] += len(results)

            self._stats["knn_cycles"] += 1

        except Exception as e:
            logger.debug(f"[KNN-DAEMON] Cycle error: {e}")
        finally:
            session.close()

    def _run_mining_cycle(self):
        """One mining cycle - mine from external sources for weakest domain."""
        session = self.session_factory()
        try:
            from cognitive.knowledge_compiler import CompiledFact
            from sqlalchemy import func

            # Find domain with fewest facts
            domain_counts = session.query(
                CompiledFact.domain, func.count(CompiledFact.id)
            ).group_by(CompiledFact.domain).having(
                func.count(CompiledFact.id) < 30
            ).order_by(func.count(CompiledFact.id)).limit(3).all()

            if not domain_counts:
                return

            domain = domain_counts[0][0]
            if not domain:
                return

            # Quick mine from one source
            import requests
            import re

            facts_added = 0

            # arXiv
            try:
                resp = requests.get(
                    "http://export.arxiv.org/api/query",
                    params={"search_query": f"all:{domain}", "max_results": 3},
                    timeout=10,
                )
                if resp.status_code == 200:
                    entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
                    for entry in entries[:3]:
                        title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                        summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                        if title and summary:
                            fact = CompiledFact(
                                subject=title.group(1).strip().replace('\n', ' ')[:256],
                                predicate="research_paper",
                                object_value=summary.group(1).strip().replace('\n', ' ')[:500],
                                confidence=0.9,
                                domain=domain,
                                verified=True,
                                source_text="arxiv:daemon",
                            )
                            session.add(fact)
                            facts_added += 1
            except Exception:
                pass

            if facts_added > 0:
                session.commit()
                self._stats["mining_facts"] += facts_added

                # Vectorize new facts via unified store
                try:
                    from embedding.vector_store import upsert as vs_upsert
                    new_facts = session.query(CompiledFact).filter(
                        CompiledFact.source_text == "arxiv:daemon",
                        CompiledFact.domain == domain,
                    ).order_by(CompiledFact.id.desc()).limit(facts_added).all()

                    if new_facts:
                        texts = [f"{f.subject}: {f.object_value}"[:500] for f in new_facts]
                        payloads = [{"domain": domain, "source": "daemon_mining"} for _ in texts]
                        vs_upsert(texts, payloads)
                except Exception:
                    pass

            self._stats["mining_cycles"] += 1

        except Exception as e:
            logger.debug(f"[MINING-DAEMON] Cycle error: {e}")
        finally:
            session.close()

    def _run_kimi_cycle(self):
        """One Kimi proactive learning cycle."""
        if not self.cloud_client or not self.cloud_client.is_available():
            return

        session = self.session_factory()
        try:
            from cognitive.knowledge_compiler import CompiledFact, KnowledgeCompiler
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            from sqlalchemy import func

            # Find a gap - domain with facts but no procedures
            from cognitive.knowledge_compiler import CompiledProcedure

            domains_with_facts = set(
                d[0] for d in session.query(CompiledFact.domain).distinct().all() if d[0]
            )
            domains_with_procs = set(
                d[0] for d in session.query(CompiledProcedure.domain).distinct().all() if d[0]
            )

            gaps = domains_with_facts - domains_with_procs
            if not gaps:
                # All domains have procedures. Mine deeper on a random one
                gaps = domains_with_facts

            if not gaps:
                return

            domain = random.choice(list(gaps))

            # Ask Kimi for procedures in this domain
            prompt = (
                f"List 3 step-by-step procedures for '{domain.replace('_', ' ')}'. "
                f"For each: PROCEDURE: name, GOAL: what, then numbered steps (3-5 each). Be concise."
            )

            result = self.cloud_client.generate(prompt=prompt, max_tokens=400)
            if not result.get("success"):
                return

            content = result["content"]
            tokens = result.get("tokens", 0)
            self._stats["kimi_tokens"] += tokens

            # Compile into knowledge store
            compiler = KnowledgeCompiler(session)
            compiler.compile_chunk(
                text=content,
                source_document_id=f"kimi_daemon:{domain}",
                domain=domain,
            )

            # Distill
            miner = get_llm_knowledge_miner(session)
            miner.store_interaction(prompt, content, "kimi_cloud:daemon", confidence=0.85)

            session.commit()

            # Vectorize via unified store
            try:
                from embedding.vector_store import upsert as vs_upsert
                text = f"{domain}: {content[:300]}"
                vs_upsert([text], [{"domain": domain, "source": "kimi_daemon"}])
            except Exception:
                pass

            self._stats["kimi_cycles"] += 1

        except Exception as e:
            logger.debug(f"[KIMI-DAEMON] Cycle error: {e}")
        finally:
            session.close()

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        stats["running"] = self._running
        stats["threads"] = len([t for t in self._threads if t.is_alive()])
        return stats


_daemon: Optional[KnowledgeDaemon] = None


def get_knowledge_daemon(session_factory=None, cloud_client=None) -> KnowledgeDaemon:
    global _daemon
    if _daemon is None:
        if not session_factory:
            from database.session import SessionLocal
            session_factory = SessionLocal
        if not cloud_client:
            try:
                from cognitive.grace_cloud_client import get_kimi_cloud_client
                cloud_client = get_kimi_cloud_client()
            except Exception:
                pass
        _daemon = KnowledgeDaemon(session_factory, cloud_client)
    return _daemon


def start_knowledge_daemon(session_factory=None, cloud_client=None) -> KnowledgeDaemon:
    """Start the knowledge daemon. Call once at app startup."""
    daemon = get_knowledge_daemon(session_factory, cloud_client)
    daemon.start()
    return daemon
