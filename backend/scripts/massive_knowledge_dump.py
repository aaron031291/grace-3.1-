#!/usr/bin/env python3
"""
Massive Knowledge Dump - Deep extraction across all SE + AI domains.

Target: 50-100 depth score per domain.

Depth formula:
  depth = min(100, facts*1.0 + procedures*2.0 + rules*1.5 + entities*1.5)
  (capped at 50 facts, 10 procedures, 10 rules, 10 entities)

To reach 50 depth: ~30 facts + 5 procedures + 3 rules + 5 entities
To reach 100 depth: ~50 facts + 10 procedures + 10 rules + 10 entities

Strategy:
  Phase 1: GitHub massive dump (repos, READMEs, code) - bulk facts + entities
  Phase 2: Multi-source discovery (wikidata, arxiv, openalex, SO) - cross-verified facts
  Phase 3: Cloud deep mine (targeted questions) - procedures + rules + depth
  Phase 4: Check depth, re-mine shallow domains
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType

config = DatabaseConfig(db_type=DatabaseType.SQLITE, database_path="data/documents.db")
DatabaseConnection.initialize(config)

from database.migrate_all import run_all_migrations
run_all_migrations()

from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

engine_db = DatabaseConnection.get_engine()
SessionFactory = sessionmaker(bind=engine_db)

from cognitive.knowledge_compiler import (
    CompiledFact, CompiledProcedure, CompiledDecisionRule,
    CompiledEntityRelation, KnowledgeCompiler,
)

# All target domains for SE + AI
DOMAINS = [
    # Software Engineering Core
    "software architecture",
    "design patterns",
    "clean code",
    "testing",
    "continuous integration",
    "microservices",
    "API design",
    "databases",
    "security",
    "devops",
    # AI/ML
    "machine learning",
    "deep learning",
    "natural language processing",
    "computer vision",
    "reinforcement learning",
    # Infrastructure
    "docker",
    "kubernetes",
    "cloud computing",
    # Data
    "data engineering",
    "distributed systems",
]

# GitHub search terms (more specific for better results)
GITHUB_TOPICS = [
    "software architecture patterns",
    "design patterns python",
    "clean code principles",
    "testing framework",
    "CI CD pipeline",
    "microservices architecture",
    "REST API best practices",
    "database optimization",
    "application security",
    "devops automation",
    "machine learning framework",
    "deep learning pytorch",
    "NLP transformer",
    "computer vision detection",
    "reinforcement learning",
    "docker containerization",
    "kubernetes deployment",
    "cloud native",
    "data pipeline ETL",
    "distributed computing",
]


def get_depth(session, domain):
    """Calculate depth score for a domain."""
    domain_variants = [domain, domain.replace(" ", "_")]
    fc = session.query(func.count(CompiledFact.id)).filter(
        CompiledFact.domain.in_(domain_variants)
    ).scalar() or 0
    pc = session.query(func.count(CompiledProcedure.id)).filter(
        CompiledProcedure.domain.in_(domain_variants)
    ).scalar() or 0
    rc = session.query(func.count(CompiledDecisionRule.id)).filter(
        CompiledDecisionRule.domain.in_(domain_variants)
    ).scalar() or 0
    ec = session.query(func.count(CompiledEntityRelation.id)).filter(
        CompiledEntityRelation.domain.in_(domain_variants)
    ).scalar() or 0

    depth = min(100, (
        min(fc, 50) * 1.0 +
        min(pc, 10) * 2.0 +
        min(rc, 10) * 1.5 +
        min(ec, 10) * 1.5
    ))
    return {"facts": fc, "procedures": pc, "rules": rc, "entities": ec, "depth": round(depth, 1)}


def report_all_depths():
    """Report depth scores for all domains."""
    session = SessionFactory()
    print("\n" + "=" * 70)
    print("DOMAIN DEPTH REPORT")
    print("=" * 70)
    total_facts = 0
    total_procs = 0
    total_rules = 0
    total_ents = 0
    for domain in sorted(DOMAINS):
        d = get_depth(session, domain)
        total_facts += d["facts"]
        total_procs += d["procedures"]
        total_rules += d["rules"]
        total_ents += d["entities"]
        bar = "#" * int(d["depth"] / 2)
        status = "OK" if d["depth"] >= 50 else "LOW" if d["depth"] >= 25 else "EMPTY"
        print(f"  [{status:5s}] {domain:30s} depth={d['depth']:5.1f}  "
              f"F={d['facts']:3d} P={d['procedures']:2d} R={d['rules']:2d} E={d['entities']:2d}  {bar}")

    # Also check existing domains
    all_domains = session.query(CompiledFact.domain).distinct().all()
    existing = set(d[0] for d in all_domains if d[0])
    target_set = set(d.replace(" ", "_") for d in DOMAINS) | set(DOMAINS)
    extra = existing - target_set
    if extra:
        print(f"\n  Other domains: {', '.join(sorted(extra)[:10])}")

    tf = session.query(func.count(CompiledFact.id)).scalar() or 0
    tp = session.query(func.count(CompiledProcedure.id)).scalar() or 0
    tr = session.query(func.count(CompiledDecisionRule.id)).scalar() or 0
    te = session.query(func.count(CompiledEntityRelation.id)).scalar() or 0
    print(f"\n  TOTALS: Facts={tf} Procedures={tp} Rules={tr} Entities={te}")
    print("=" * 70)
    session.close()


def phase1_github_dump():
    """Phase 1: Massive GitHub dump for bulk facts."""
    print("\n" + "=" * 70)
    print("PHASE 1: GITHUB MASSIVE DUMP")
    print("=" * 70)

    import requests

    session = SessionFactory()
    total_repos = 0
    total_facts = 0

    for topic in GITHUB_TOPICS:
        domain = topic.split()[0] + "_" + topic.split()[-1] if len(topic.split()) > 1 else topic
        # Map to our domain names
        domain_map = {
            "software architecture patterns": "software_architecture",
            "design patterns python": "design_patterns",
            "clean code principles": "clean_code",
            "testing framework": "testing",
            "CI CD pipeline": "continuous_integration",
            "microservices architecture": "microservices",
            "REST API best practices": "API_design",
            "database optimization": "databases",
            "application security": "security",
            "devops automation": "devops",
            "machine learning framework": "machine_learning",
            "deep learning pytorch": "deep_learning",
            "NLP transformer": "natural_language_processing",
            "computer vision detection": "computer_vision",
            "reinforcement learning": "reinforcement_learning",
            "docker containerization": "docker",
            "kubernetes deployment": "kubernetes",
            "cloud native": "cloud_computing",
            "data pipeline ETL": "data_engineering",
            "distributed computing": "distributed_systems",
        }
        domain = domain_map.get(topic, topic.replace(" ", "_"))

        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": topic, "sort": "stars", "order": "desc", "per_page": 5},
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=15,
            )

            if resp.status_code == 403:
                print(f"  [RATE LIMITED] Waiting 60s...")
                time.sleep(60)
                continue

            if resp.status_code != 200:
                print(f"  [SKIP] {topic}: HTTP {resp.status_code}")
                time.sleep(2)
                continue

            repos = resp.json().get("items", [])
            topic_facts = 0

            for repo in repos[:5]:
                repo_name = repo.get("full_name", "")
                stars = repo.get("stargazers_count", 0)
                description = repo.get("description", "") or ""
                language = repo.get("language", "") or ""

                # Store repo fact
                fact = CompiledFact(
                    subject=repo_name[:256],
                    predicate="github_repo",
                    object_value=f"{description[:500]}. Language: {language}. Stars: {stars}",
                    confidence=min(0.95, 0.5 + stars / 10000),
                    domain=domain,
                    verified=True,
                    source_text=f"github:{repo.get('html_url', '')}",
                    tags={"source": "github", "stars": stars, "language": language},
                )
                session.add(fact)

                # Entity relationship
                entity = CompiledEntityRelation(
                    entity_a=domain.replace("_", " ")[:256],
                    relation="implemented_by",
                    entity_b=repo_name[:256],
                    confidence=min(0.9, 0.5 + stars / 10000),
                    domain=domain,
                )
                session.add(entity)
                topic_facts += 1

                # Get README
                try:
                    readme_resp = requests.get(
                        f"https://api.github.com/repos/{repo_name}/readme",
                        headers={"Accept": "application/vnd.github.v3.raw"},
                        timeout=10,
                    )
                    if readme_resp.status_code == 200 and readme_resp.text:
                        readme_text = readme_resp.text[:3000]
                        compiler = KnowledgeCompiler(session)
                        compiled = compiler.compile_chunk(
                            text=readme_text,
                            source_document_id=f"github:{repo_name}",
                            domain=domain,
                        )
                        for k, v in compiled.items():
                            if isinstance(v, list):
                                topic_facts += len(v)
                except Exception:
                    pass

                total_repos += 1
                time.sleep(0.3)

            session.commit()
            total_facts += topic_facts
            print(f"  [OK] {topic:40s} repos={len(repos[:5])} facts={topic_facts}")
            time.sleep(1.5)  # GitHub rate limiting

        except Exception as e:
            print(f"  [ERR] {topic}: {str(e)[:60]}")

    session.close()
    print(f"\n  Phase 1 complete: {total_repos} repos, {total_facts} facts")


def phase2_multi_source():
    """Phase 2: Multi-source discovery (wikidata, arxiv, openalex, SO)."""
    print("\n" + "=" * 70)
    print("PHASE 2: MULTI-SOURCE DISCOVERY")
    print("=" * 70)

    import requests
    import re

    session = SessionFactory()
    total_facts = 0

    for domain in DOMAINS:
        domain_key = domain.replace(" ", "_")
        domain_facts = 0

        # arXiv
        try:
            resp = requests.get(
                "http://export.arxiv.org/api/query",
                params={"search_query": f"all:{domain}", "max_results": 3, "sortBy": "relevance"},
                timeout=15,
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
                            domain=domain_key,
                            verified=True,
                            source_text="arxiv",
                        )
                        session.add(fact)
                        domain_facts += 1
        except Exception:
            pass

        # OpenAlex
        try:
            resp = requests.get(
                "https://api.openalex.org/works",
                params={"search": domain, "per_page": 3, "sort": "cited_by_count:desc"},
                headers={"User-Agent": "GraceOS/1.0"},
                timeout=15,
            )
            if resp.status_code == 200:
                for w in resp.json().get("results", [])[:3]:
                    if w.get("title"):
                        fact = CompiledFact(
                            subject=w["title"][:256],
                            predicate="scholarly_work",
                            object_value=f"Cited {w.get('cited_by_count', 0)} times. Domain: {domain}",
                            confidence=min(0.95, 0.5 + w.get("cited_by_count", 0) / 1000),
                            domain=domain_key,
                            verified=True,
                            source_text="openalex",
                        )
                        session.add(fact)
                        domain_facts += 1
        except Exception:
            pass

        # StackOverflow
        try:
            resp = requests.get(
                "https://api.stackexchange.com/2.3/search",
                params={"intitle": domain, "site": "stackoverflow",
                        "pagesize": 3, "order": "desc", "sort": "votes"},
                timeout=10,
            )
            if resp.status_code == 200:
                for item in resp.json().get("items", [])[:3]:
                    fact = CompiledFact(
                        subject=item.get("title", "")[:256],
                        predicate="community_knowledge",
                        object_value=f"Score: {item.get('score', 0)}. "
                                     f"Answered: {item.get('is_answered', False)}. "
                                     f"Tags: {', '.join(item.get('tags', [])[:5])}",
                        confidence=min(0.85, 0.4 + item.get("score", 0) / 100),
                        domain=domain_key,
                        verified=item.get("is_answered", False),
                        source_text="stackoverflow",
                    )
                    session.add(fact)
                    domain_facts += 1
        except Exception:
            pass

        # Wikidata
        try:
            resp = requests.get(
                "https://www.wikidata.org/w/api.php",
                params={
                    "action": "wbsearchentities", "search": domain,
                    "language": "en", "limit": 3, "format": "json",
                },
                headers={"User-Agent": "GraceOS/1.0 (knowledge mining)"},
                timeout=10,
            )
            if resp.status_code == 200:
                for item in resp.json().get("search", [])[:3]:
                    fact = CompiledFact(
                        subject=item.get("label", domain)[:256],
                        predicate="wikidata_entity",
                        object_value=item.get("description", "")[:500],
                        confidence=1.0,
                        domain=domain_key,
                        verified=True,
                        source_text=f"wikidata:{item.get('id', '')}",
                    )
                    session.add(fact)

                    entity = CompiledEntityRelation(
                        entity_a=domain[:256],
                        relation="described_by",
                        entity_b=item.get("label", "")[:256],
                        confidence=1.0,
                        domain=domain_key,
                    )
                    session.add(entity)
                    domain_facts += 1
        except Exception:
            pass

        session.commit()
        total_facts += domain_facts
        print(f"  [OK] {domain:30s} +{domain_facts} facts (arxiv+openalex+SO+wikidata)")
        time.sleep(0.5)

    session.close()
    print(f"\n  Phase 2 complete: {total_facts} facts from external sources")


def phase3_cloud_deep_mine():
    """Phase 3: Cloud API deep mine for procedures, rules, and depth."""
    print("\n" + "=" * 70)
    print("PHASE 3: CLOUD DEEP MINE (procedures + rules + depth)")
    print("=" * 70)

    try:
        from cognitive.grace_cloud_client import get_kimi_cloud_client
        cloud = get_kimi_cloud_client()
        if not cloud or not cloud.is_available():
            print("  [SKIP] Cloud API not available")
            return
    except Exception as e:
        print(f"  [SKIP] Cloud client error: {e}")
        return

    session = SessionFactory()
    total_tokens = 0

    for domain in DOMAINS:
        domain_key = domain.replace(" ", "_")
        d = get_depth(session, domain)

        # Skip domains already at target depth
        if d["depth"] >= 50:
            print(f"  [SKIP] {domain:30s} depth={d['depth']} (already at target)")
            continue

        # Determine what's needed
        needs_procedures = d["procedures"] < 5
        needs_rules = d["rules"] < 5
        needs_facts = d["facts"] < 30

        prompts = []

        if needs_facts:
            prompts.append(
                f"List 10 key technical facts about {domain} in software engineering. "
                f"Format each as a single sentence starting with a capitalized subject. "
                f"Be specific and precise. No numbering."
            )

        if needs_procedures:
            prompts.append(
                f"List 5 step-by-step procedures commonly used in {domain}. "
                f"For each procedure, give:\n"
                f"PROCEDURE: [name]\n"
                f"GOAL: [what it achieves]\n"
                f"1. [step 1]\n2. [step 2]\n3. [step 3]\n"
                f"Keep each procedure to 3-5 steps."
            )

        if needs_rules:
            prompts.append(
                f"List 5 decision rules used in {domain}. "
                f"Format each as:\n"
                f"IF [condition] THEN [action] ELSE [alternative]\n"
                f"Be specific and actionable."
            )

        for prompt in prompts:
            if not cloud.is_available():
                print(f"  [RATE] Cloud rate limited, waiting...")
                time.sleep(10)
                if not cloud.is_available():
                    break

            try:
                result = cloud.generate(prompt=prompt, max_tokens=600)
                if not result.get("success"):
                    continue

                content = result["content"]
                tokens = result.get("tokens", 0)
                total_tokens += tokens

                # Compile the response
                compiler = KnowledgeCompiler(session)
                compiled = compiler.compile_chunk(
                    text=content,
                    source_document_id=f"cloud_deep:{domain_key}",
                    domain=domain_key,
                )

                # Also store as distilled knowledge
                try:
                    from cognitive.knowledge_compiler import get_llm_knowledge_miner
                    miner = get_llm_knowledge_miner(session)
                    miner.store_interaction(prompt, content, "kimi_cloud:deep_mine", confidence=0.85)
                except Exception:
                    pass

                session.commit()
                time.sleep(1)

            except Exception as e:
                print(f"  [ERR] {domain}: {str(e)[:60]}")

        d_after = get_depth(session, domain)
        print(f"  [OK] {domain:30s} depth: {d['depth']:5.1f} -> {d_after['depth']:5.1f}  "
              f"(F={d_after['facts']} P={d_after['procedures']} R={d_after['rules']} E={d_after['entities']})")

    session.close()
    print(f"\n  Phase 3 complete: {total_tokens} cloud tokens used")


def phase4_fill_gaps():
    """Phase 4: Fill remaining gaps with targeted extraction."""
    print("\n" + "=" * 70)
    print("PHASE 4: FILL REMAINING GAPS")
    print("=" * 70)

    session = SessionFactory()
    shallow = []

    for domain in DOMAINS:
        d = get_depth(session, domain)
        if d["depth"] < 50:
            shallow.append((domain, d))

    if not shallow:
        print("  All domains at target depth!")
        session.close()
        return

    print(f"  {len(shallow)} domains below target depth:")
    for domain, d in shallow:
        print(f"    {domain}: depth={d['depth']}")

    # Generate comprehensive text blocks for shallow domains
    for domain, d in shallow:
        domain_key = domain.replace(" ", "_")

        # Hard-coded comprehensive knowledge blocks
        knowledge_blocks = _get_knowledge_block(domain)

        for block in knowledge_blocks:
            compiler = KnowledgeCompiler(session)
            compiler.compile_chunk(
                text=block,
                source_document_id=f"manual:{domain_key}",
                domain=domain_key,
            )

        session.commit()

        d_after = get_depth(session, domain)
        print(f"  [OK] {domain:30s} depth: {d['depth']:5.1f} -> {d_after['depth']:5.1f}")

    session.close()


def _get_knowledge_block(domain):
    """Get comprehensive knowledge text for a domain."""
    blocks = {
        "software architecture": [
            "Software Architecture is the high-level structure of a software system. "
            "Monolithic architecture uses a single codebase for all functionality. "
            "Microservices architecture decomposes applications into independent services. "
            "Event-driven architecture uses events to trigger and communicate between services. "
            "Layered architecture separates concerns into presentation, business, and data layers. "
            "Hexagonal architecture isolates business logic from external concerns using ports and adapters. "
            "CQRS separates read and write operations for scalability. "
            "Event sourcing stores all changes as a sequence of events. "
            "Domain-driven design aligns software architecture with business domains. "
            "The SOLID principles guide software architecture decisions.",
            "PROCEDURE: Design System Architecture\n"
            "GOAL: Create a robust system architecture\n"
            "1. Identify functional requirements and quality attributes\n"
            "2. Choose an architectural style (monolith, microservices, event-driven)\n"
            "3. Define component boundaries and interfaces\n"
            "4. Design data flow and communication patterns\n"
            "5. Document architecture decisions with ADRs",
            "PROCEDURE: Evaluate Architecture\n"
            "GOAL: Assess architecture fitness\n"
            "1. Define quality attribute scenarios (performance, scalability, security)\n"
            "2. Run ATAM (Architecture Tradeoff Analysis Method)\n"
            "3. Identify architectural risks and tradeoffs\n"
            "4. Create architecture fitness functions\n"
            "5. Implement automated architecture tests",
            "If the system needs to scale independently then use microservices architecture. "
            "If the system has complex business rules then use domain-driven design. "
            "If real-time processing is needed then use event-driven architecture. "
            "When starting a new project you should begin with a modular monolith. "
            "If the team is small then use a monolithic architecture to reduce complexity.",
        ],
        "design patterns": [
            "Design Patterns are reusable solutions to common software design problems. "
            "The Singleton pattern ensures a class has only one instance. "
            "The Factory Method pattern creates objects without specifying exact classes. "
            "The Observer pattern defines a one-to-many dependency between objects. "
            "The Strategy pattern encapsulates interchangeable algorithms. "
            "The Decorator pattern adds behavior to objects dynamically. "
            "The Adapter pattern converts one interface to another. "
            "The Command pattern encapsulates a request as an object. "
            "The Repository pattern abstracts data access behind a collection-like interface. "
            "The Builder pattern constructs complex objects step by step.",
            "PROCEDURE: Apply Design Pattern\n"
            "GOAL: Solve a recurring design problem\n"
            "1. Identify the design problem and forces\n"
            "2. Match the problem to a pattern category (creational, structural, behavioral)\n"
            "3. Select the most appropriate pattern\n"
            "4. Implement the pattern with proper abstractions\n"
            "5. Verify the solution doesn't over-engineer",
            "If you need exactly one instance then use the Singleton pattern. "
            "If object creation is complex then use the Factory or Builder pattern. "
            "If you need to notify multiple objects of changes then use Observer. "
            "When algorithms vary at runtime you should use the Strategy pattern. "
            "If you need to add behavior without modifying existing code then use Decorator.",
        ],
        "clean code": [
            "Clean Code is code that is easy to read, understand, and maintain. "
            "Functions should do one thing and do it well. "
            "Variable names should reveal intent and be pronounceable. "
            "Comments should explain why, not what. "
            "The DRY principle means Don't Repeat Yourself. "
            "KISS means Keep It Simple Stupid. "
            "YAGNI means You Ain't Gonna Need It. "
            "Code smells indicate deeper problems in the design. "
            "Refactoring improves code structure without changing behavior. "
            "Boy Scout Rule says leave the code cleaner than you found it.",
            "PROCEDURE: Refactor Legacy Code\n"
            "GOAL: Improve code quality safely\n"
            "1. Write characterization tests for existing behavior\n"
            "2. Identify code smells (long methods, large classes, feature envy)\n"
            "3. Apply extract method refactoring for long methods\n"
            "4. Apply extract class for large classes\n"
            "5. Run all tests to verify behavior preserved",
            "If a function exceeds 20 lines then extract smaller functions. "
            "If a class has more than one responsibility then split it. "
            "When naming variables you should use descriptive names over abbreviations. "
            "If code is duplicated then extract a shared function or class. "
            "If a comment explains what code does then the code should be rewritten to be self-documenting.",
        ],
        "testing": [
            "Unit Testing verifies individual components in isolation. "
            "Integration Testing verifies component interactions. "
            "End-to-end Testing verifies the complete system workflow. "
            "Test-Driven Development writes tests before implementation. "
            "Behavior-Driven Development uses natural language test specifications. "
            "Mock objects simulate dependencies for isolated testing. "
            "Code coverage measures the percentage of code exercised by tests. "
            "Property-based testing generates random inputs to find edge cases. "
            "Mutation testing introduces bugs to verify test effectiveness. "
            "The test pyramid suggests many unit tests, fewer integration, fewest E2E.",
            "PROCEDURE: Write Unit Tests\n"
            "GOAL: Verify component behavior\n"
            "1. Arrange test data and dependencies\n"
            "2. Act by calling the method under test\n"
            "3. Assert expected outcomes\n"
            "4. Test edge cases and error conditions\n"
            "5. Verify test independence (no shared state)",
            "PROCEDURE: Implement TDD\n"
            "GOAL: Drive design through tests\n"
            "1. Write a failing test for the next requirement\n"
            "2. Write minimal code to make the test pass\n"
            "3. Refactor while keeping tests green\n"
            "4. Repeat the red-green-refactor cycle",
            "If a function has side effects then use mocks for testing. "
            "If test setup is complex then use test fixtures or factories. "
            "When coverage is below 80% you should add tests for uncovered paths. "
            "If tests are slow then separate unit tests from integration tests. "
            "If a bug is found then write a regression test before fixing it.",
        ],
        "continuous integration": [
            "Continuous Integration merges code changes frequently into a shared repository. "
            "CI pipelines automate build, test, and validation on every commit. "
            "Continuous Delivery extends CI to automatically prepare releases. "
            "Continuous Deployment automatically deploys every passing change to production. "
            "Feature flags enable trunk-based development by hiding incomplete features. "
            "Pipeline stages typically include lint, unit test, integration test, build, deploy. "
            "Artifact management stores versioned build outputs. "
            "Blue-green deployment runs two identical production environments. "
            "Canary releases gradually route traffic to new versions. "
            "GitOps uses Git as the single source of truth for deployments.",
            "PROCEDURE: Set Up CI Pipeline\n"
            "GOAL: Automate code validation\n"
            "1. Configure version control hooks (pre-commit, push triggers)\n"
            "2. Add lint and static analysis stage\n"
            "3. Add unit test stage with coverage reporting\n"
            "4. Add integration test stage\n"
            "5. Add build and artifact storage stage",
            "If builds take too long then parallelize test execution. "
            "If deployments are risky then use canary releases. "
            "When merging to main you should require all CI checks to pass. "
            "If feature is incomplete then use feature flags instead of long-lived branches.",
        ],
        "microservices": [
            "Microservices decompose applications into small, independent services. "
            "Each microservice owns its own data and database. "
            "Service discovery enables services to find each other dynamically. "
            "API gateways provide a single entry point for client requests. "
            "Circuit breakers prevent cascading failures between services. "
            "Saga pattern manages distributed transactions across services. "
            "Service mesh provides infrastructure-level communication management. "
            "Sidecar pattern deploys helper processes alongside service containers. "
            "Strangler fig pattern incrementally migrates monoliths to microservices. "
            "Bounded contexts from DDD define microservice boundaries.",
            "PROCEDURE: Decompose Monolith\n"
            "GOAL: Migrate to microservices\n"
            "1. Identify bounded contexts in the business domain\n"
            "2. Extract the most independent module first\n"
            "3. Define API contracts between the new service and monolith\n"
            "4. Implement data migration and synchronization\n"
            "5. Deploy and route traffic gradually using strangler fig",
            "If services need synchronous communication then use REST or gRPC. "
            "If services need asynchronous communication then use message queues. "
            "When a service fails you should use circuit breakers to prevent cascading. "
            "If data consistency across services is needed then use the Saga pattern.",
        ],
        "API design": [
            "REST APIs use HTTP methods to perform CRUD operations on resources. "
            "GraphQL provides a single endpoint with flexible query language. "
            "gRPC uses Protocol Buffers for high-performance RPC communication. "
            "API versioning prevents breaking changes for existing clients. "
            "Rate limiting protects APIs from abuse and overload. "
            "OAuth 2.0 is the standard for API authorization. "
            "OpenAPI Specification documents REST API contracts. "
            "HATEOAS includes hypermedia links in API responses for discoverability. "
            "Pagination handles large result sets with offset or cursor-based approaches. "
            "Idempotency ensures repeated requests produce the same result.",
            "PROCEDURE: Design REST API\n"
            "GOAL: Create a well-structured API\n"
            "1. Define resources and their relationships\n"
            "2. Map HTTP methods to operations (GET, POST, PUT, DELETE)\n"
            "3. Design URL structure following REST conventions\n"
            "4. Define request/response schemas with OpenAPI\n"
            "5. Implement error handling with standard HTTP status codes",
            "If the API serves mobile clients then use GraphQL for efficient data fetching. "
            "If performance is critical then use gRPC with Protocol Buffers. "
            "When introducing breaking changes you should version the API. "
            "If the API is public then implement rate limiting and API keys.",
        ],
        "databases": [
            "Relational Databases store data in tables with SQL access. "
            "NoSQL Databases handle unstructured data with flexible schemas. "
            "ACID properties ensure reliable database transactions. "
            "BASE properties provide eventual consistency for distributed databases. "
            "Database indexing speeds up query performance using B-trees or hash indexes. "
            "Database sharding distributes data across multiple servers. "
            "Connection pooling reuses database connections for performance. "
            "ORM frameworks map database tables to programming language objects. "
            "Database migrations version control schema changes. "
            "Read replicas scale read-heavy workloads.",
            "PROCEDURE: Optimize Database Query\n"
            "GOAL: Improve query performance\n"
            "1. Run EXPLAIN ANALYZE on the slow query\n"
            "2. Identify missing indexes from the query plan\n"
            "3. Add covering indexes for frequent queries\n"
            "4. Rewrite N+1 queries to use JOINs or batch loading\n"
            "5. Consider materialized views for complex aggregations",
            "If data is highly relational then use PostgreSQL or MySQL. "
            "If the schema changes frequently then use MongoDB or DynamoDB. "
            "When queries are slow you should check the execution plan for missing indexes. "
            "If read throughput is a bottleneck then add read replicas.",
        ],
        "security": [
            "Authentication verifies user identity through credentials or tokens. "
            "Authorization determines what authenticated users can access. "
            "JWT tokens enable stateless authentication with signed claims. "
            "OWASP Top 10 lists the most critical web application security risks. "
            "SQL injection attacks insert malicious SQL through user input. "
            "XSS attacks inject malicious scripts into web pages. "
            "CSRF attacks trick users into performing unintended actions. "
            "Encryption at rest protects stored data using AES or similar algorithms. "
            "TLS encrypts data in transit between client and server. "
            "Zero trust architecture assumes no implicit trust in any network segment.",
            "PROCEDURE: Implement Authentication\n"
            "GOAL: Secure user access\n"
            "1. Choose authentication method (JWT, OAuth, session-based)\n"
            "2. Hash passwords with bcrypt or Argon2\n"
            "3. Implement token refresh mechanism\n"
            "4. Add rate limiting to login endpoints\n"
            "5. Enable multi-factor authentication for sensitive operations",
            "If handling user passwords then use bcrypt with salt. "
            "If the API is public then implement OAuth 2.0 with scopes. "
            "When accepting user input you should sanitize to prevent SQL injection. "
            "If data is sensitive then encrypt at rest and in transit.",
        ],
        "devops": [
            "Infrastructure as Code manages infrastructure through version-controlled definitions. "
            "Terraform provisions cloud resources declaratively. "
            "Ansible automates configuration management across servers. "
            "Monitoring tracks system health with metrics, logs, and traces. "
            "Prometheus collects time-series metrics from services. "
            "Grafana visualizes monitoring data in dashboards. "
            "ELK stack aggregates and searches log data. "
            "Incident management processes restore service during outages. "
            "SRE practices balance reliability with development velocity. "
            "Chaos engineering proactively tests system resilience.",
            "PROCEDURE: Set Up Monitoring\n"
            "GOAL: Achieve observability\n"
            "1. Instrument application code with metrics (latency, errors, throughput)\n"
            "2. Deploy Prometheus for metrics collection\n"
            "3. Create Grafana dashboards for key metrics\n"
            "4. Set up alerting rules for SLO violations\n"
            "5. Implement distributed tracing with Jaeger or Zipkin",
            "If infrastructure changes are needed then use Terraform. "
            "If server configuration needs automation then use Ansible. "
            "When an incident occurs you should follow the incident management process. "
            "If system reliability is critical then implement SLOs and error budgets.",
        ],
        "machine learning": [
            "Supervised Learning trains models on labeled data. "
            "Unsupervised Learning finds patterns in unlabeled data. "
            "Feature engineering transforms raw data into model inputs. "
            "Overfitting occurs when a model memorizes training data. "
            "Cross-validation evaluates model performance on unseen data. "
            "Gradient descent optimizes model parameters iteratively. "
            "Random forests combine multiple decision trees for robust predictions. "
            "Support vector machines find optimal decision boundaries. "
            "Ensemble methods combine multiple models for better accuracy. "
            "MLOps applies DevOps practices to machine learning workflows.",
            "PROCEDURE: Train ML Model\n"
            "GOAL: Build a predictive model\n"
            "1. Collect and clean training data\n"
            "2. Perform exploratory data analysis and feature engineering\n"
            "3. Split data into train, validation, and test sets\n"
            "4. Train model and tune hyperparameters\n"
            "5. Evaluate on test set and deploy if performance meets threshold",
            "If the data is labeled then use supervised learning. "
            "If you need to find groups in data then use clustering. "
            "When the model overfits you should add regularization or more training data. "
            "If features are correlated then apply PCA for dimensionality reduction.",
        ],
        "deep learning": [
            "Neural Networks consist of layers of interconnected neurons. "
            "Convolutional Neural Networks excel at image processing tasks. "
            "Recurrent Neural Networks process sequential data. "
            "Transformers use self-attention for parallel sequence processing. "
            "Backpropagation computes gradients for neural network training. "
            "Batch normalization stabilizes and accelerates training. "
            "Dropout prevents overfitting by randomly deactivating neurons. "
            "Transfer learning reuses pretrained models for new tasks. "
            "GANs generate realistic data by training competing networks. "
            "Attention mechanisms allow models to focus on relevant input parts.",
            "PROCEDURE: Fine-tune Pretrained Model\n"
            "GOAL: Adapt model to specific task\n"
            "1. Select a pretrained model (BERT, ResNet, GPT)\n"
            "2. Prepare domain-specific training data\n"
            "3. Freeze base layers and train classifier head\n"
            "4. Gradually unfreeze layers for fine-tuning\n"
            "5. Evaluate and compare against baseline",
            "If working with images then use CNNs or Vision Transformers. "
            "If working with text then use Transformer models. "
            "When training is unstable you should reduce learning rate. "
            "If dataset is small then use transfer learning from a pretrained model.",
        ],
        "natural language processing": [
            "Tokenization splits text into words or subword units. "
            "Word Embeddings represent words as dense vectors. "
            "Named Entity Recognition identifies entities like names and locations. "
            "Sentiment Analysis determines emotional tone of text. "
            "BERT provides bidirectional contextual word representations. "
            "GPT generates text autoregressively. "
            "Retrieval-Augmented Generation combines search with generation. "
            "Prompt Engineering designs effective inputs for language models. "
            "Text Classification assigns categories to documents. "
            "Machine Translation converts text between languages.",
            "PROCEDURE: Build Text Classifier\n"
            "GOAL: Classify documents automatically\n"
            "1. Collect and label training documents\n"
            "2. Preprocess text (tokenize, clean, normalize)\n"
            "3. Generate embeddings (TF-IDF, Word2Vec, or BERT)\n"
            "4. Train classifier (Naive Bayes, SVM, or fine-tuned transformer)\n"
            "5. Evaluate with precision, recall, and F1 score",
            "If accuracy is critical then use fine-tuned transformer models. "
            "If speed matters more than accuracy then use TF-IDF with linear classifiers. "
            "When building a chatbot you should use retrieval-augmented generation.",
        ],
        "computer vision": [
            "Image Classification assigns labels to entire images. "
            "Object Detection locates and classifies objects within images. "
            "Semantic Segmentation labels every pixel in an image. "
            "Image Augmentation increases training data variety artificially. "
            "YOLO performs real-time object detection. "
            "ResNet introduced skip connections for training very deep networks. "
            "Feature Pyramids handle objects at multiple scales. "
            "Optical Flow estimates motion between video frames. "
            "GAN-based super-resolution increases image resolution. "
            "Vision Transformers apply attention to image patches.",
            "PROCEDURE: Train Object Detector\n"
            "GOAL: Detect objects in images\n"
            "1. Collect and annotate images with bounding boxes\n"
            "2. Choose a detection architecture (YOLO, Faster R-CNN, SSD)\n"
            "3. Apply data augmentation (flip, rotate, crop, color jitter)\n"
            "4. Train with appropriate loss function (focal loss, IoU loss)\n"
            "5. Evaluate with mAP metric at various IoU thresholds",
            "If real-time detection is needed then use YOLO. "
            "If accuracy is more important than speed then use Faster R-CNN. "
            "When training data is limited you should use heavy data augmentation.",
        ],
        "reinforcement learning": [
            "Reinforcement Learning trains agents through trial and error. "
            "The reward signal guides agent behavior. "
            "Q-learning estimates action values for state-action pairs. "
            "Policy gradient methods optimize the policy directly. "
            "Deep Q-Networks combine Q-learning with neural networks. "
            "Actor-critic methods combine value and policy learning. "
            "Exploration-exploitation tradeoff balances trying new actions vs known good ones. "
            "Markov Decision Processes formalize sequential decision problems. "
            "Monte Carlo tree search plans by simulating future outcomes. "
            "Multi-agent RL handles multiple interacting agents.",
            "PROCEDURE: Train RL Agent\n"
            "GOAL: Learn optimal behavior\n"
            "1. Define the environment (states, actions, rewards)\n"
            "2. Choose algorithm (DQN, PPO, A3C)\n"
            "3. Implement reward shaping for faster learning\n"
            "4. Train with sufficient exploration\n"
            "5. Evaluate with multiple random seeds",
            "If the action space is discrete then use DQN. "
            "If the action space is continuous then use PPO or SAC. "
            "When the agent doesn't explore enough you should increase exploration rate.",
        ],
        "docker": [
            "Docker containers package applications with their dependencies. "
            "Dockerfile defines the steps to build a container image. "
            "Docker Compose orchestrates multi-container applications. "
            "Docker volumes persist data beyond container lifecycle. "
            "Docker networks enable container-to-container communication. "
            "Multi-stage builds reduce final image size. "
            "Docker Hub is the default container image registry. "
            "Container health checks monitor application readiness. "
            "Docker Swarm provides native container orchestration. "
            "Distroless images minimize attack surface by removing OS packages.",
            "PROCEDURE: Containerize Application\n"
            "GOAL: Package app as Docker container\n"
            "1. Create a Dockerfile with appropriate base image\n"
            "2. Copy application code and install dependencies\n"
            "3. Use multi-stage build to minimize image size\n"
            "4. Configure environment variables and expose ports\n"
            "5. Build image and test locally with docker run",
            "If the image is too large then use multi-stage builds. "
            "If containers need shared data then use Docker volumes. "
            "When running in production you should use health checks. "
            "If security is a concern then use distroless or Alpine base images.",
        ],
        "kubernetes": [
            "Kubernetes orchestrates containerized applications at scale. "
            "Pods are the smallest deployable units in Kubernetes. "
            "Deployments manage the desired state of pod replicas. "
            "Services provide stable networking for pod communication. "
            "Ingress manages external HTTP access to services. "
            "ConfigMaps and Secrets manage application configuration. "
            "Horizontal Pod Autoscaler scales pods based on metrics. "
            "Namespaces isolate resources within a cluster. "
            "Helm packages Kubernetes applications as reusable charts. "
            "Operators extend Kubernetes with custom controllers.",
            "PROCEDURE: Deploy to Kubernetes\n"
            "GOAL: Run application on K8s cluster\n"
            "1. Create Deployment manifest with container spec\n"
            "2. Create Service for internal networking\n"
            "3. Create Ingress for external access\n"
            "4. Configure resource limits and requests\n"
            "5. Set up health checks (liveness and readiness probes)",
            "If pods crash frequently then check resource limits and liveness probes. "
            "If you need auto-scaling then configure Horizontal Pod Autoscaler. "
            "When deploying updates you should use rolling deployment strategy. "
            "If the cluster has multiple teams then use namespaces for isolation.",
        ],
        "cloud computing": [
            "IaaS provides virtual infrastructure (compute, storage, networking). "
            "PaaS provides platforms for application deployment. "
            "SaaS delivers software as a hosted service. "
            "Serverless computing executes functions without managing servers. "
            "Auto-scaling adjusts resources based on demand. "
            "Load balancing distributes traffic across multiple instances. "
            "CDN caches content at edge locations for faster delivery. "
            "Cloud-native applications are designed for cloud environments. "
            "Multi-cloud strategy uses multiple cloud providers. "
            "The shared responsibility model divides security between provider and customer.",
            "PROCEDURE: Migrate to Cloud\n"
            "GOAL: Move on-premise application to cloud\n"
            "1. Assess application cloud readiness (the 6 Rs)\n"
            "2. Choose migration strategy (rehost, replatform, refactor)\n"
            "3. Set up cloud infrastructure with IaC\n"
            "4. Migrate data with minimal downtime\n"
            "5. Validate functionality and performance post-migration",
            "If you want zero server management then use serverless. "
            "If you need full infrastructure control then use IaaS. "
            "When costs are rising you should right-size instances and use reserved capacity.",
        ],
        "data engineering": [
            "ETL extracts data from sources, transforms it, and loads it into targets. "
            "Data Pipelines automate data flow between systems. "
            "Data Lakes store raw data in its native format. "
            "Data Warehouses store structured data optimized for analytics. "
            "Apache Kafka enables real-time data streaming. "
            "Apache Spark provides distributed data processing. "
            "Data Quality ensures accuracy, completeness, and consistency. "
            "Data Governance manages data policies and compliance. "
            "Schema Registry manages data schema evolution. "
            "Batch processing handles large volumes of data periodically.",
            "PROCEDURE: Build Data Pipeline\n"
            "GOAL: Automate data processing\n"
            "1. Identify data sources and formats\n"
            "2. Design pipeline stages (extract, validate, transform, load)\n"
            "3. Implement error handling and retry logic\n"
            "4. Add data quality checks between stages\n"
            "5. Schedule and monitor pipeline execution",
            "If real-time data processing is needed then use Kafka Streams or Flink. "
            "If processing large batch data then use Apache Spark. "
            "When data quality issues occur you should add validation checks.",
        ],
        "distributed systems": [
            "The CAP theorem states you can have at most two of consistency, availability, partition tolerance. "
            "Consensus algorithms like Raft enable agreement in distributed systems. "
            "Consistent hashing distributes data evenly across nodes. "
            "Vector clocks track causality in distributed events. "
            "Two-phase commit coordinates distributed transactions. "
            "Eventual consistency guarantees all replicas converge. "
            "Leader election selects a coordinator among distributed nodes. "
            "Gossip protocols disseminate information in peer-to-peer networks. "
            "Distributed caching reduces load on backend services. "
            "MapReduce processes large datasets in parallel across clusters.",
            "PROCEDURE: Design Distributed System\n"
            "GOAL: Build scalable distributed application\n"
            "1. Identify consistency and availability requirements\n"
            "2. Choose appropriate consistency model\n"
            "3. Design partitioning and replication strategy\n"
            "4. Implement failure detection and recovery\n"
            "5. Add distributed tracing for observability",
            "If strong consistency is required then use consensus algorithms. "
            "If availability is more important then use eventual consistency. "
            "When network partitions occur you should handle them gracefully.",
        ],
    }
    return blocks.get(domain, [
        f"{domain} is a critical area of software engineering and AI. "
        f"Practitioners use established methodologies and tools. "
        f"Best practices include testing, documentation, and iterative development.",
    ])


if __name__ == "__main__":
    print("=" * 70)
    print("GRACE MASSIVE KNOWLEDGE DUMP")
    print(f"Target: 50-100 depth across {len(DOMAINS)} domains")
    print(f"Domains: {', '.join(DOMAINS[:5])}... and {len(DOMAINS)-5} more")
    print("=" * 70)

    report_all_depths()

    print("\nStarting 4-phase extraction...\n")

    phase1_github_dump()
    report_all_depths()

    phase2_multi_source()
    report_all_depths()

    phase3_cloud_deep_mine()
    report_all_depths()

    phase4_fill_gaps()

    print("\n\nFINAL REPORT:")
    report_all_depths()
