"""
Grace Knowledge Engine - ONE unified knowledge system.

Consolidates:
  - Knowledge Compiler     (raw text → facts, procedures, rules)
  - Knowledge Mining Engine (parallel multi-source extraction)
  - Knowledge Exhaustion   (convergence-based deep extraction)
  - Library Connectors     (Wikidata, ConceptNet, Wolfram)
  - Kimi Teacher           (cloud API for novel knowledge)
  - Vector Dedup           (existing Qdrant embeddings as foundation)
  - Kimi Audit             (identify gaps, depth assessment)
  - Reverse KNN            (find related knowledge via vector similarity)

ONE class. ONE API surface. No more losing track.

Usage:
    engine = GraceKnowledgeEngine(session_factory)

    # Discover - mine knowledge from all sources
    engine.discover("machine learning")

    # Exhaust - extract until convergence
    engine.exhaust("docker", max_cycles=3)

    # Audit - Kimi identifies what's missing
    engine.audit_gaps()

    # Query - deterministic lookup (no LLM)
    engine.query("What is the default port for Qdrant?")

    # Reverse KNN - find related knowledge via vector similarity
    engine.reverse_knn("design patterns", limit=10)

    # GitHub dump - massive one-time injection
    engine.github_dump(["fastapi", "sqlalchemy", "qdrant"])

    # Stats - unified view of all knowledge
    engine.stats()
"""

import logging
import hashlib
import time
import os
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class GraceKnowledgeEngine:
    """
    Single unified knowledge engine for Grace.

    All knowledge flows through here:
      INGEST → COMPILE → DEDUP (vector) → STORE → INDEX

    Existing vectors in Qdrant serve as the FOUNDATION.
    New knowledge is compared against them before storage.
    """

    def __init__(self, session_factory, cloud_client=None):
        self.session_factory = session_factory
        self.cloud_client = cloud_client
        self._stats = {
            "queries": 0,
            "facts_compiled": 0,
            "facts_deduplicated": 0,
            "topics_exhausted": 0,
            "topics_audited": 0,
            "github_repos_mined": 0,
            "library_queries": 0,
            "cloud_tokens_used": 0,
            "vector_comparisons": 0,
        }

    # ==================================================================
    # QUERY - deterministic lookup, no LLM
    # ==================================================================

    def query(self, question: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Query compiled knowledge. Deterministic. No LLM needed.

        Searches facts, procedures, rules, and distilled knowledge.
        """
        self._stats["queries"] += 1
        session = self.session_factory()
        results = {"facts": [], "procedures": [], "rules": [], "distilled": None}

        try:
            from cognitive.knowledge_compiler import (
                CompiledFact, CompiledProcedure, CompiledDecisionRule,
            )

            keywords = [w.lower() for w in question.split() if len(w) > 2]

            # Search facts
            fact_query = session.query(CompiledFact)
            if domain:
                fact_query = fact_query.filter(CompiledFact.domain == domain)
            for kw in keywords[:3]:
                fact_query = fact_query.filter(
                    CompiledFact.subject.ilike(f"%{kw}%") |
                    CompiledFact.object_value.ilike(f"%{kw}%")
                )
            facts = fact_query.order_by(CompiledFact.confidence.desc()).limit(10).all()
            results["facts"] = [
                {"subject": f.subject, "predicate": f.predicate,
                 "object": f.object_value, "confidence": f.confidence,
                 "domain": f.domain, "verified": f.verified}
                for f in facts
            ]

            # Search procedures
            proc_query = session.query(CompiledProcedure)
            if domain:
                proc_query = proc_query.filter(CompiledProcedure.domain == domain)
            for kw in keywords[:2]:
                proc_query = proc_query.filter(
                    CompiledProcedure.name.ilike(f"%{kw}%") |
                    CompiledProcedure.goal.ilike(f"%{kw}%")
                )
            procs = proc_query.limit(5).all()
            results["procedures"] = [
                {"name": p.name, "goal": p.goal, "steps": p.steps, "confidence": p.confidence}
                for p in procs
            ]

            # Search rules
            rule_query = session.query(CompiledDecisionRule)
            if domain:
                rule_query = rule_query.filter(CompiledDecisionRule.domain == domain)
            for kw in keywords[:2]:
                rule_query = rule_query.filter(
                    CompiledDecisionRule.rule_name.ilike(f"%{kw}%")
                )
            rules = rule_query.limit(5).all()
            results["rules"] = [
                {"name": r.rule_name, "action": r.action, "conditions": r.conditions}
                for r in rules
            ]

            # Check distilled knowledge (cached LLM answers)
            try:
                from cognitive.knowledge_compiler import DistilledKnowledge
                distilled = session.query(DistilledKnowledge).filter(
                    DistilledKnowledge.query_text.ilike(f"%{keywords[0]}%")
                ).order_by(DistilledKnowledge.confidence.desc()).first()
                if distilled:
                    results["distilled"] = {
                        "query": distilled.query_text,
                        "response": distilled.response_text,
                        "confidence": distilled.confidence,
                    }
            except Exception:
                pass

        except Exception as e:
            results["error"] = str(e)[:200]
        finally:
            session.close()

        results["total_results"] = (
            len(results["facts"]) + len(results["procedures"]) +
            len(results["rules"]) + (1 if results["distilled"] else 0)
        )
        return results

    # ==================================================================
    # DISCOVER - mine knowledge from all available sources
    # ==================================================================

    def discover(
        self,
        topic: str,
        sources: Optional[List[str]] = None,
        max_per_source: int = 5,
    ) -> Dict[str, Any]:
        """
        Discover knowledge about a topic from multiple sources.

        Sources: cloud, wikidata, conceptnet, github, arxiv, openalex, stackoverflow
        New facts are deduped against existing vectors before storage.
        """
        if sources is None:
            sources = ["cloud", "wikidata", "conceptnet", "github", "arxiv"]

        session = self.session_factory()
        all_results = {}
        total_new = 0
        total_dupes = 0

        existing_hashes = self._get_fact_hashes(session, topic)

        for source in sources:
            try:
                if source == "cloud":
                    facts = self._discover_from_cloud(topic, max_per_source)
                elif source == "wikidata":
                    facts = self._discover_from_wikidata(topic, max_per_source)
                elif source == "conceptnet":
                    facts = self._discover_from_conceptnet(topic, max_per_source)
                elif source == "github":
                    facts = self._discover_from_github(topic, max_per_source)
                elif source == "arxiv":
                    facts = self._discover_from_arxiv(topic, max_per_source)
                elif source == "openalex":
                    facts = self._discover_from_openalex(topic, max_per_source)
                elif source == "stackoverflow":
                    facts = self._discover_from_stackoverflow(topic, max_per_source)
                else:
                    continue

                # Dedup against existing knowledge
                new_facts = []
                for fact in facts:
                    h = self._hash_fact(fact)
                    if h not in existing_hashes:
                        # Vector similarity check against Qdrant
                        if not self._is_semantically_duplicate(fact):
                            existing_hashes.add(h)
                            new_facts.append(fact)
                            total_new += 1
                        else:
                            total_dupes += 1
                            self._stats["facts_deduplicated"] += 1
                    else:
                        total_dupes += 1

                # Store new facts
                if new_facts:
                    self._store_facts(session, new_facts, topic, source)

                all_results[source] = {
                    "found": len(facts),
                    "new": len(new_facts),
                    "duplicates": len(facts) - len(new_facts),
                }

            except Exception as e:
                all_results[source] = {"error": str(e)[:100]}

        session.commit()
        session.close()

        return {
            "topic": topic,
            "sources_queried": len(sources),
            "total_found": total_new + total_dupes,
            "total_new": total_new,
            "total_duplicates": total_dupes,
            "by_source": all_results,
        }

    # ==================================================================
    # REVERSE KNN - find related knowledge via vector similarity
    # ==================================================================

    def reverse_knn(
        self, query: str, limit: int = 10, threshold: float = 0.4,
        include_subagents: bool = False,
    ) -> Dict[str, Any]:
        """
        Reverse KNN: find knowledge related to a query using vector similarity.

        Searches existing Qdrant vectors and optionally runs the full
        KNN sub-agent swarm (vector + web + API + cross-domain).

        Returns ranked results with similarity scores.
        """
        results = {"query": query, "vector_results": [], "subagent_results": []}

        # Vector search via unified store (cloud or local)
        try:
            from embedding.vector_store import search as vs_search
            hits = vs_search(query, limit=limit, threshold=threshold)
            results["vector_results"] = hits
        except Exception as e:
            results["vector_error"] = str(e)[:100]

        # KNN sub-agent swarm
        if include_subagents:
            try:
                from cognitive.knn_subagent_engine import KNNSubAgentOrchestrator
                orchestrator = KNNSubAgentOrchestrator()
                swarm_result = orchestrator.discover(query, depth=1)
                if hasattr(swarm_result, "discoveries_by_source"):
                    results["subagent_results"] = [
                        {
                            "topic": d.topic,
                            "text": d.text[:300],
                            "source": d.source,
                            "trust": d.trust_score,
                            "similarity": d.similarity,
                        }
                        for d in getattr(swarm_result, "all_discoveries", [])[:limit]
                    ]
            except Exception as e:
                results["subagent_error"] = str(e)[:100]

        results["total_results"] = len(results["vector_results"]) + len(results["subagent_results"])
        return results

    # ==================================================================
    # EXHAUST - convergence-based deep extraction
    # ==================================================================

    def exhaust(
        self,
        topic: str,
        max_cycles: int = 3,
        questions_per_cycle: int = 5,
        convergence_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Extract knowledge until convergence.

        Algorithm:
        1. Ask questions from 30+ different perspectives
        2. Extract facts from each answer
        3. Dedup against existing vectors + fact hashes
        4. If >80% answers repeat existing knowledge → converging
        5. 5 consecutive converged questions → cycle converged
        6. 3 converged cycles → topic EXHAUSTED
        7. Then try GitHub for remaining novel facts
        """
        from cognitive.knowledge_exhaustion_engine import (
            get_knowledge_exhaustion_engine,
        )
        engine = get_knowledge_exhaustion_engine(self.session_factory, self.cloud_client)
        result = engine.exhaust_topic(topic, max_cycles, questions_per_cycle, convergence_threshold)
        if result.get("exhausted"):
            self._stats["topics_exhausted"] += 1
        return result

    def exhaust_multiple(self, topics: List[str], **kwargs) -> Dict[str, Any]:
        """Exhaust multiple topics sequentially."""
        from cognitive.knowledge_exhaustion_engine import get_knowledge_exhaustion_engine
        engine = get_knowledge_exhaustion_engine(self.session_factory, self.cloud_client)
        return engine.exhaust_multiple(topics, **kwargs)

    # ==================================================================
    # GITHUB DUMP - massive one-time injection
    # ==================================================================

    def github_dump(
        self,
        topics: List[str],
        max_repos: int = 10,
        max_files: int = 3,
    ) -> Dict[str, Any]:
        """
        Massive GitHub dump. Pulls top repos, READMEs, code files.
        One-time injection of external knowledge.
        """
        from cognitive.knowledge_exhaustion_engine import get_knowledge_exhaustion_engine
        engine = get_knowledge_exhaustion_engine(self.session_factory, self.cloud_client)
        result = engine.github_massive_dump(topics, max_repos, max_files)
        self._stats["github_repos_mined"] += result.get("total_repos", 0)
        return result

    # ==================================================================
    # AUDIT - Kimi identifies what's missing
    # ==================================================================

    def audit_gaps(self, domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Kimi audits the knowledge store to find:
        1. Topics with low fact count (shallow knowledge)
        2. Topics with no procedures (can't execute)
        3. Topics with no rules (can't decide)
        4. Domains that exist but have gaps
        5. Cross-domain connections that are missing
        6. Depth assessment for each topic

        Returns actionable gap report with priorities.
        """
        self._stats["topics_audited"] += 1
        session = self.session_factory()
        report = {"domains": {}, "gaps": [], "recommendations": [], "depth": {}}

        try:
            from cognitive.knowledge_compiler import (
                CompiledFact, CompiledProcedure, CompiledDecisionRule,
                CompiledEntityRelation, CompiledTopicIndex,
            )
            from cognitive.knowledge_exhaustion_engine import TopicExhaustionTracker

            # Get all domains and their counts
            domain_facts = session.query(
                CompiledFact.domain, func.count(CompiledFact.id)
            ).group_by(CompiledFact.domain).all()

            domain_procs = session.query(
                CompiledProcedure.domain, func.count(CompiledProcedure.id)
            ).group_by(CompiledProcedure.domain).all()

            domain_rules = session.query(
                CompiledDecisionRule.domain, func.count(CompiledDecisionRule.id)
            ).group_by(CompiledDecisionRule.domain).all()

            domain_entities = session.query(
                CompiledEntityRelation.domain, func.count(CompiledEntityRelation.id)
            ).group_by(CompiledEntityRelation.domain).all()

            # Build domain map
            all_domains = set()
            facts_map = {d: c for d, c in domain_facts if d}
            procs_map = {d: c for d, c in domain_procs if d}
            rules_map = {d: c for d, c in domain_rules if d}
            ents_map = {d: c for d, c in domain_entities if d}

            all_domains.update(facts_map.keys())
            all_domains.update(procs_map.keys())

            if domains:
                all_domains = {d for d in all_domains if d in domains}

            for domain in sorted(all_domains):
                fc = facts_map.get(domain, 0)
                pc = procs_map.get(domain, 0)
                rc = rules_map.get(domain, 0)
                ec = ents_map.get(domain, 0)

                # Depth score: 0-100
                depth = min(100, (
                    min(fc, 50) * 1.0 +   # facts contribute up to 50
                    min(pc, 10) * 2.0 +    # procedures contribute up to 20
                    min(rc, 10) * 1.5 +    # rules contribute up to 15
                    min(ec, 10) * 1.5      # entities contribute up to 15
                ))

                report["domains"][domain] = {
                    "facts": fc,
                    "procedures": pc,
                    "rules": rc,
                    "entities": ec,
                    "depth_score": round(depth, 1),
                    "depth_label": self._depth_label(depth),
                }

                report["depth"][domain] = round(depth, 1)

                # Identify specific gaps
                if fc == 0:
                    report["gaps"].append({
                        "domain": domain,
                        "type": "no_facts",
                        "severity": "critical",
                        "message": f"Domain '{domain}' has zero facts",
                    })
                elif fc < 10:
                    report["gaps"].append({
                        "domain": domain,
                        "type": "shallow_facts",
                        "severity": "high",
                        "message": f"Domain '{domain}' has only {fc} facts (need 10+)",
                    })

                if pc == 0 and fc > 5:
                    report["gaps"].append({
                        "domain": domain,
                        "type": "no_procedures",
                        "severity": "medium",
                        "message": f"Domain '{domain}' has facts but no procedures",
                    })

                if rc == 0 and fc > 10:
                    report["gaps"].append({
                        "domain": domain,
                        "type": "no_rules",
                        "severity": "medium",
                        "message": f"Domain '{domain}' has {fc} facts but no decision rules",
                    })

            # Check exhaustion tracker
            try:
                trackers = session.query(TopicExhaustionTracker).all()
                for t in trackers:
                    if t.status != "exhausted":
                        report["gaps"].append({
                            "domain": t.topic,
                            "type": "not_exhausted",
                            "severity": "low",
                            "message": f"Topic '{t.topic}' is {t.status} (convergence: {t.convergence_count}/3)",
                        })
            except Exception:
                pass

            # Get totals
            total_facts = session.query(func.count(CompiledFact.id)).scalar() or 0
            total_procs = session.query(func.count(CompiledProcedure.id)).scalar() or 0
            total_rules = session.query(func.count(CompiledDecisionRule.id)).scalar() or 0
            total_ents = session.query(func.count(CompiledEntityRelation.id)).scalar() or 0

            # Qdrant vector count
            vector_count = self._get_vector_count()

            report["totals"] = {
                "facts": total_facts,
                "procedures": total_procs,
                "rules": total_rules,
                "entities": total_ents,
                "vectors": vector_count,
                "domains": len(all_domains),
                "gaps": len(report["gaps"]),
            }

            # Ask Kimi for recommendations if available
            if self.cloud_client and self.cloud_client.is_available() and report["gaps"]:
                kimi_recommendations = self._ask_kimi_for_gap_analysis(report)
                if kimi_recommendations:
                    report["recommendations"] = kimi_recommendations

            # Sort gaps by severity
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            report["gaps"].sort(key=lambda g: severity_order.get(g["severity"], 4))

        except Exception as e:
            report["error"] = str(e)[:200]
        finally:
            session.close()

        return report

    def audit_depth(self, topic: str) -> Dict[str, Any]:
        """
        Deep audit of a single topic. Uses Kimi to assess:
        - What subtopics are covered vs missing
        - What depth level the knowledge is at (intro/intermediate/expert)
        - What questions the current knowledge CAN answer
        - What questions it CANNOT answer
        """
        session = self.session_factory()
        result = {"topic": topic, "coverage": {}, "can_answer": [], "cannot_answer": []}

        try:
            from cognitive.knowledge_compiler import CompiledFact

            facts = session.query(CompiledFact).filter(
                CompiledFact.domain.in_([topic, topic.replace(" ", "_")])
            ).all()

            subjects = set()
            for f in facts:
                subjects.add(f.subject.lower())

            result["fact_count"] = len(facts)
            result["unique_subjects"] = len(subjects)
            result["subjects"] = sorted(subjects)[:50]

            if self.cloud_client and self.cloud_client.is_available():
                subject_summary = ", ".join(sorted(subjects)[:30])
                prompt = (
                    f"I have knowledge about '{topic}' covering these subjects: "
                    f"{subject_summary}\n\n"
                    f"Total facts: {len(facts)}\n\n"
                    f"Assess:\n"
                    f"1. DEPTH LEVEL: beginner/intermediate/advanced/expert\n"
                    f"2. MISSING SUBTOPICS: List 5 critical subtopics NOT covered\n"
                    f"3. QUESTIONS I CAN answer with this knowledge (list 3)\n"
                    f"4. QUESTIONS I CANNOT answer yet (list 5)\n"
                    f"5. PRIORITY: What should I learn next about {topic}?\n"
                    f"Be concise. One line per item."
                )

                resp = self.cloud_client.generate(prompt=prompt, max_tokens=400)
                if resp.get("success"):
                    result["kimi_assessment"] = resp["content"]
                    self._stats["cloud_tokens_used"] += resp.get("tokens", 0)

                    # Distill the assessment
                    self._distill(session, prompt, resp["content"])

        except Exception as e:
            result["error"] = str(e)[:200]
        finally:
            session.close()

        return result

    # ==================================================================
    # MINE CODEBASE - extract code patterns, API signatures, error fixes
    # ==================================================================

    def mine_codebase(self, root_path: str = "/workspace/backend") -> Dict[str, Any]:
        """
        Mine source code for actionable patterns:
        - Function signatures with types and decorators
        - Class patterns with inheritance and init params
        - Error handling patterns (try/except)
        - Framework-specific patterns (FastAPI, SQLAlchemy, Qdrant, pytest)
        - Error-solution pairs for common bugs
        """
        from cognitive.code_pattern_miner import CodePatternMiner
        miner = CodePatternMiner(self.session_factory)

        codebase = miner.mine_codebase(root_path)
        frameworks = miner.mine_framework_patterns()
        errors = miner.mine_error_solutions()

        return {
            "codebase": codebase,
            "framework_patterns": frameworks["patterns_stored"],
            "error_solutions": errors["error_solutions_stored"],
            "stats": miner.get_stats(),
        }

    # ==================================================================
    # COMPILE - raw text → structured knowledge
    # ==================================================================

    def compile(
        self, text: str, domain: Optional[str] = None,
        source_id: Optional[str] = None, vectorize: bool = True,
    ) -> Dict[str, Any]:
        """
        Compile raw text into structured knowledge + vectorize.

        Uses heuristic extraction (no LLM needed).
        New facts are deduped against existing vectors.
        """
        session = self.session_factory()
        try:
            from cognitive.knowledge_compiler import KnowledgeCompiler
            compiler = KnowledgeCompiler(session)
            result = compiler.compile_chunk(text, source_id, domain=domain)

            if vectorize:
                text_preview = text[:500]
                self._vectorize(text_preview, {
                    "source": source_id or "manual",
                    "domain": domain or "general",
                    "type": "compiled",
                })

            session.commit()
            self._stats["facts_compiled"] += len(result.get("facts", []))
            return result
        except Exception as e:
            return {"error": str(e)[:200]}
        finally:
            session.close()

    # ==================================================================
    # STATS - unified view
    # ==================================================================

    def stats(self) -> Dict[str, Any]:
        """Unified knowledge stats across all subsystems."""
        session = self.session_factory()
        result = dict(self._stats)

        try:
            from cognitive.knowledge_compiler import (
                CompiledFact, CompiledProcedure, CompiledDecisionRule,
                CompiledEntityRelation,
            )

            result["store"] = {
                "facts": session.query(func.count(CompiledFact.id)).scalar() or 0,
                "procedures": session.query(func.count(CompiledProcedure.id)).scalar() or 0,
                "rules": session.query(func.count(CompiledDecisionRule.id)).scalar() or 0,
                "entities": session.query(func.count(CompiledEntityRelation.id)).scalar() or 0,
            }

            # Top domains
            top_domains = session.query(
                CompiledFact.domain, func.count(CompiledFact.id)
            ).group_by(CompiledFact.domain).order_by(
                func.count(CompiledFact.id).desc()
            ).limit(10).all()
            result["top_domains"] = {d: c for d, c in top_domains if d}

            # Exhaustion status
            try:
                from cognitive.knowledge_exhaustion_engine import TopicExhaustionTracker
                result["exhaustion"] = {
                    "tracked": session.query(func.count(TopicExhaustionTracker.id)).scalar() or 0,
                    "exhausted": session.query(func.count(TopicExhaustionTracker.id)).filter(
                        TopicExhaustionTracker.status == "exhausted"
                    ).scalar() or 0,
                }
            except Exception:
                pass

            result["vectors"] = self._get_vector_count()

        except Exception as e:
            result["error"] = str(e)[:200]
        finally:
            session.close()

        return result

    # ==================================================================
    # TOPIC STATUS
    # ==================================================================

    def topic_status(self, topic: str) -> Dict[str, Any]:
        """Get complete status for a topic: facts, depth, exhaustion, vectors."""
        session = self.session_factory()
        status = {"topic": topic}

        try:
            from cognitive.knowledge_compiler import (
                CompiledFact, CompiledProcedure, CompiledDecisionRule,
                CompiledEntityRelation,
            )
            domain_variants = [topic, topic.replace(" ", "_")]

            status["facts"] = session.query(func.count(CompiledFact.id)).filter(
                CompiledFact.domain.in_(domain_variants)
            ).scalar() or 0

            status["procedures"] = session.query(func.count(CompiledProcedure.id)).filter(
                CompiledProcedure.domain.in_(domain_variants)
            ).scalar() or 0

            status["rules"] = session.query(func.count(CompiledDecisionRule.id)).filter(
                CompiledDecisionRule.domain.in_(domain_variants)
            ).scalar() or 0

            status["entities"] = session.query(func.count(CompiledEntityRelation.id)).filter(
                CompiledEntityRelation.domain.in_(domain_variants)
            ).scalar() or 0

            depth = min(100, (
                min(status["facts"], 50) * 1.0 +
                min(status["procedures"], 10) * 2.0 +
                min(status["rules"], 10) * 1.5 +
                min(status["entities"], 10) * 1.5
            ))
            status["depth_score"] = round(depth, 1)
            status["depth_label"] = self._depth_label(depth)

            # Check exhaustion
            try:
                from cognitive.knowledge_exhaustion_engine import TopicExhaustionTracker
                tracker = session.query(TopicExhaustionTracker).filter_by(topic=topic).first()
                if tracker:
                    status["exhaustion"] = {
                        "status": tracker.status,
                        "cycles": tracker.cycles_completed,
                        "convergence": tracker.convergence_count,
                        "questions_asked": tracker.total_questions,
                    }
                else:
                    status["exhaustion"] = {"status": "not_started"}
            except Exception:
                pass

        except Exception as e:
            status["error"] = str(e)[:200]
        finally:
            session.close()

        return status

    # ==================================================================
    # INTERNAL - source-specific discovery
    # ==================================================================

    def _discover_from_cloud(self, topic: str, limit: int) -> List[Dict]:
        if not self.cloud_client or not self.cloud_client.is_available():
            return []

        prompt = (
            f"List {limit} key facts about '{topic}'. "
            f"Format each as: SUBJECT | PREDICATE | OBJECT\n"
            f"Example: Python | created_by | Guido van Rossum\n"
            f"Only factual, verifiable information."
        )

        resp = self.cloud_client.generate(prompt=prompt, max_tokens=400)
        if not resp.get("success"):
            return []

        self._stats["cloud_tokens_used"] += resp.get("tokens", 0)
        facts = []
        for line in resp["content"].split("\n"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                facts.append({
                    "subject": parts[0][:256],
                    "predicate": parts[1][:256],
                    "object": parts[2][:500],
                    "source": "kimi_cloud",
                    "confidence": 0.8,
                })
        return facts[:limit]

    def _discover_from_wikidata(self, topic: str, limit: int) -> List[Dict]:
        try:
            from cognitive.library_connectors import LibraryConnectors
            lib = LibraryConnectors()
            results = lib.query_wikidata(topic, limit=limit)
            self._stats["library_queries"] += 1
            return [
                {"subject": r.get("subject", topic), "predicate": r.get("predicate", "related"),
                 "object": str(r.get("object", "")), "source": "wikidata",
                 "confidence": r.get("confidence", 0.95)}
                for r in results
            ]
        except Exception:
            return []

    def _discover_from_conceptnet(self, topic: str, limit: int) -> List[Dict]:
        try:
            from cognitive.library_connectors import LibraryConnectors
            lib = LibraryConnectors()
            results = lib.query_conceptnet(topic, limit=limit)
            self._stats["library_queries"] += 1
            return [
                {"subject": r.get("subject", topic), "predicate": r.get("predicate", "related"),
                 "object": str(r.get("object", "")), "source": "conceptnet",
                 "confidence": r.get("confidence", 0.85)}
                for r in results
            ]
        except Exception:
            return []

    def _discover_from_github(self, topic: str, limit: int) -> List[Dict]:
        try:
            import requests as req
            resp = req.get(
                "https://api.github.com/search/repositories",
                params={"q": topic, "sort": "stars", "per_page": min(limit, 5)},
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            facts = []
            for item in resp.json().get("items", [])[:limit]:
                facts.append({
                    "subject": item.get("full_name", ""),
                    "predicate": "github_repo",
                    "object": f"{item.get('description', '') or ''}. "
                              f"Stars: {item.get('stargazers_count', 0)}. "
                              f"Language: {item.get('language', '')}",
                    "source": "github",
                    "confidence": min(0.9, 0.5 + item.get("stargazers_count", 0) / 10000),
                })
            self._stats["library_queries"] += 1
            return facts
        except Exception:
            return []

    def _discover_from_arxiv(self, topic: str, limit: int) -> List[Dict]:
        try:
            import requests as req
            resp = req.get(
                "http://export.arxiv.org/api/query",
                params={"search_query": f"all:{topic}", "max_results": min(limit, 3)},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            facts = []
            entries = re.findall(r'<entry>(.*?)</entry>', resp.text, re.DOTALL)
            for entry in entries[:limit]:
                title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                summary = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                if title and summary:
                    facts.append({
                        "subject": title.group(1).strip().replace('\n', ' ')[:256],
                        "predicate": "research_paper",
                        "object": summary.group(1).strip().replace('\n', ' ')[:500],
                        "source": "arxiv",
                        "confidence": 0.9,
                    })
            self._stats["library_queries"] += 1
            return facts
        except Exception:
            return []

    def _discover_from_openalex(self, topic: str, limit: int) -> List[Dict]:
        try:
            import requests as req
            resp = req.get(
                "https://api.openalex.org/works",
                params={"search": topic, "per_page": min(limit, 3)},
                headers={"User-Agent": "GraceOS/1.0"},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            facts = []
            for w in resp.json().get("results", [])[:limit]:
                if w.get("title"):
                    facts.append({
                        "subject": w["title"][:256],
                        "predicate": "scholarly_work",
                        "object": f"Cited {w.get('cited_by_count', 0)} times",
                        "source": "openalex",
                        "confidence": min(0.95, 0.5 + w.get("cited_by_count", 0) / 1000),
                    })
            self._stats["library_queries"] += 1
            return facts
        except Exception:
            return []

    def _discover_from_stackoverflow(self, topic: str, limit: int) -> List[Dict]:
        try:
            import requests as req
            resp = req.get(
                "https://api.stackexchange.com/2.3/search",
                params={"intitle": topic, "site": "stackoverflow",
                        "pagesize": min(limit, 3), "order": "desc", "sort": "votes"},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            facts = []
            for item in resp.json().get("items", [])[:limit]:
                facts.append({
                    "subject": item.get("title", "")[:256],
                    "predicate": "stackoverflow_question",
                    "object": f"Score: {item.get('score', 0)}, "
                              f"Answered: {item.get('is_answered', False)}",
                    "source": "stackoverflow",
                    "confidence": min(0.85, 0.4 + item.get("score", 0) / 100),
                })
            self._stats["library_queries"] += 1
            return facts
        except Exception:
            return []

    # ==================================================================
    # INTERNAL - storage, dedup, vectorization
    # ==================================================================

    def _store_facts(self, session: Session, facts: List[Dict], topic: str, source: str):
        """Store facts in compiled knowledge store."""
        try:
            from cognitive.knowledge_compiler import CompiledFact, CompiledEntityRelation

            for fact in facts:
                cf = CompiledFact(
                    subject=str(fact.get("subject", ""))[:256],
                    predicate=str(fact.get("predicate", "related"))[:256],
                    object_value=str(fact.get("object", ""))[:2000],
                    confidence=fact.get("confidence", 0.5),
                    domain=topic.replace(" ", "_"),
                    verified=fact.get("confidence", 0.5) > 0.8,
                    source_text=f"{source}:{fact.get('subject', '')[:100]}",
                    tags={"source": source, "engine": "grace_knowledge_engine"},
                )
                session.add(cf)
                self._stats["facts_compiled"] += 1

                # Vectorize
                text = f"{fact.get('subject', '')}: {fact.get('object', '')}"
                self._vectorize(text[:500], {
                    "source": source,
                    "domain": topic,
                    "subject": fact.get("subject", ""),
                    "confidence": fact.get("confidence", 0.5),
                })

        except Exception as e:
            logger.debug(f"[KNOWLEDGE] Store error: {e}")

    def _get_fact_hashes(self, session: Session, topic: str) -> Set[str]:
        """Get hashes of existing facts for dedup."""
        try:
            from cognitive.knowledge_compiler import CompiledFact
            domain_variants = [topic, topic.replace(" ", "_")]
            facts = session.query(CompiledFact).filter(
                CompiledFact.domain.in_(domain_variants)
            ).all()
            return {self._hash_fact({"subject": f.subject, "object": f.object_value}) for f in facts}
        except Exception:
            return set()

    def _hash_fact(self, fact: Dict) -> str:
        """Normalized hash for fact dedup."""
        subj = str(fact.get("subject", "")).lower().strip()[:50]
        obj = str(fact.get("object", fact.get("object_value", ""))).lower().strip()[:100]
        normalized = re.sub(r'\s+', ' ', f"{subj}:{obj}")
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def _is_semantically_duplicate(self, fact: Dict) -> bool:
        """Check if a fact is semantically similar to existing vectors."""
        self._stats["vector_comparisons"] += 1
        try:
            from embedding.vector_store import search
            text = f"{fact.get('subject', '')}: {fact.get('object', '')}"[:300]
            results = search(text, limit=1, threshold=0.92)
            return len(results) > 0
        except Exception:
            return False

    def _vectorize(self, text: str, metadata: Dict[str, Any]):
        """Store text + embedding in vector store (cloud or local)."""
        try:
            from embedding.vector_store import upsert
            upsert([text[:500]], [metadata])
        except Exception:
            pass

    def _get_vector_count(self) -> int:
        """Get current vector count."""
        try:
            from embedding.vector_store import count
            return count()
        except Exception:
            return 0

    def _distill(self, session: Session, question: str, answer: str):
        """Store in distilled knowledge for future deterministic lookup."""
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            miner = get_llm_knowledge_miner(session)
            miner.store_interaction(question, answer, "grace_knowledge_engine", confidence=0.8)
            session.commit()
        except Exception:
            pass

    def _ask_kimi_for_gap_analysis(self, report: Dict) -> List[Dict]:
        """Ask Kimi to analyze gaps and recommend priorities."""
        if not self.cloud_client or not self.cloud_client.is_available():
            return []

        try:
            gap_summary = "\n".join(
                f"- {g['domain']}: {g['message']}" for g in report["gaps"][:15]
            )
            domain_summary = "\n".join(
                f"- {d}: {info['facts']} facts, depth={info['depth_score']}"
                for d, info in list(report["domains"].items())[:10]
            )

            prompt = (
                f"Knowledge gap analysis:\n\n"
                f"DOMAINS:\n{domain_summary}\n\n"
                f"GAPS:\n{gap_summary}\n\n"
                f"Prioritize: which 5 gaps should be filled first? "
                f"For each, suggest the best source (cloud/wikidata/github/arxiv). "
                f"One line per recommendation. Format: PRIORITY | DOMAIN | ACTION | SOURCE"
            )

            resp = self.cloud_client.generate(prompt=prompt, max_tokens=300)
            if resp.get("success"):
                self._stats["cloud_tokens_used"] += resp.get("tokens", 0)
                recs = []
                for line in resp["content"].split("\n"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        recs.append({
                            "priority": parts[0],
                            "domain": parts[1] if len(parts) > 1 else "",
                            "action": parts[2] if len(parts) > 2 else "",
                            "source": parts[3] if len(parts) > 3 else "cloud",
                        })
                return recs[:5]
        except Exception:
            pass
        return []

    def _depth_label(self, score: float) -> str:
        if score >= 80:
            return "expert"
        elif score >= 60:
            return "advanced"
        elif score >= 35:
            return "intermediate"
        elif score >= 10:
            return "beginner"
        else:
            return "empty"


# ==================================================================
# SINGLETON
# ==================================================================

_engine: Optional[GraceKnowledgeEngine] = None

def get_grace_knowledge_engine(session_factory=None, cloud_client=None) -> GraceKnowledgeEngine:
    global _engine
    if _engine is None:
        if not session_factory:
            from database.session import SessionLocal
            session_factory = SessionLocal
        if not cloud_client:
            try:
                from cognitive.grace_cloud_client import get_kimi_cloud_client
                cloud_client = get_kimi_cloud_client()
            except Exception:
                pass
        _engine = GraceKnowledgeEngine(session_factory, cloud_client)
    return _engine
