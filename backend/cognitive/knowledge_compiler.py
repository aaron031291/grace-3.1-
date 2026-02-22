"""
Knowledge Compiler

The missing piece between raw data and Grace's deterministic execution.

Raw data (text, PDFs, code, conversations) cannot be executed on directly.
LLMs have weights and models. Grace is deterministic.
We use Kimi and LLM orchestration as TOOLS to compile knowledge ONCE,
then Grace accesses the compiled knowledge forever without needing an LLM.

THE COMPILATION PIPELINE:

    RAW DATA (text, PDFs, code, chats)
         │
         ▼
    STEP 1: INGEST + EMBED (already exists)
    Chunking, embedding, vector storage in Qdrant
    Output: Searchable vector space
         │
         ▼
    STEP 2: COMPILE (THIS MODULE - uses LLM ONCE)
    LLM reads chunks, extracts structured knowledge:
    - Facts (key-value pairs Grace can query)
    - Procedures (step-by-step executable instructions)
    - Decision rules (if X then Y, deterministic)
    - Entity relationships (A relates to B how)
    - Topic classifications (this chunk is about X)
         │
         ▼
    STEP 3: STORE IN DETERMINISTIC STRUCTURES
    - Fact tables (SQL queryable)
    - Procedure registry (executable steps)
    - Decision trees (deterministic if/then/else)
    - Topic index (fast category lookup)
    - Entity graph (relationship traversal)
         │
         ▼
    STEP 4: GRACE QUERIES DETERMINISTICALLY
    No LLM needed. Direct lookup:
    - "What is the default port for Qdrant?" → Fact table → 6333
    - "How do I fix a broken Docker build?" → Procedure registry → steps
    - "Should I use Redis or Memcached?" → Decision tree → depends on X
    - "What topics does this document cover?" → Topic index → [A, B, C]

The LLM is used ONCE during compilation (Step 2).
After that, Grace accesses compiled knowledge deterministically.
"""

import logging
import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Float, Integer, Text, JSON, Boolean, Index
from database.base import BaseModel

logger = logging.getLogger(__name__)


# ======================================================================
# COMPILED KNOWLEDGE MODELS (stored in DB, queried deterministically)
# ======================================================================

class CompiledFact(BaseModel):
    """
    A single extracted fact. Queryable without LLM.

    Examples:
        subject="Qdrant", predicate="default_port", object="6333"
        subject="Python", predicate="created_by", object="Guido van Rossum"
        subject="FastAPI", predicate="based_on", object="Starlette and Pydantic"
    """
    __tablename__ = "compiled_facts"

    subject = Column(String(256), nullable=False, index=True)
    predicate = Column(String(256), nullable=False, index=True)
    object_value = Column(Text, nullable=False)
    object_type = Column(String(64), default="text")  # text, number, boolean, list, json

    confidence = Column(Float, default=0.5)
    source_document_id = Column(String(64), nullable=True)
    source_chunk_id = Column(String(64), nullable=True)
    source_text = Column(Text, nullable=True)

    verified = Column(Boolean, default=False)
    times_accessed = Column(Integer, default=0)

    domain = Column(String(128), nullable=True, index=True)
    tags = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_facts_subject_predicate", "subject", "predicate"),
        Index("idx_facts_domain", "domain"),
    )


class CompiledProcedure(BaseModel):
    """
    An extracted procedure. Executable without LLM.

    Steps are concrete, ordered actions Grace can follow.
    """
    __tablename__ = "compiled_procedures"

    name = Column(String(256), nullable=False, index=True)
    goal = Column(Text, nullable=False)
    domain = Column(String(128), nullable=True, index=True)
    trigger_condition = Column(Text, nullable=True)

    steps = Column(JSON, nullable=False)  # [{step: 1, action: "...", detail: "..."}]
    preconditions = Column(JSON, nullable=True)
    expected_outcome = Column(Text, nullable=True)

    confidence = Column(Float, default=0.5)
    source_document_id = Column(String(64), nullable=True)

    times_executed = Column(Integer, default=0)
    times_succeeded = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_procedures_domain", "domain"),
    )


class CompiledDecisionRule(BaseModel):
    """
    A deterministic decision rule. No LLM needed to evaluate.

    Format: IF conditions THEN action ELSE alternative
    """
    __tablename__ = "compiled_decision_rules"

    rule_name = Column(String(256), nullable=False, index=True)
    domain = Column(String(128), nullable=True, index=True)

    conditions = Column(JSON, nullable=False)  # [{field: "x", operator: "==", value: "y"}]
    action = Column(Text, nullable=False)
    alternative = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    confidence = Column(Float, default=0.5)
    source_document_id = Column(String(64), nullable=True)

    times_evaluated = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_rules_domain", "domain"),
    )


class CompiledTopicIndex(BaseModel):
    """
    Topic classification for a document chunk.
    Enables fast category-based lookup without LLM.
    """
    __tablename__ = "compiled_topic_index"

    chunk_id = Column(String(64), nullable=True, index=True)
    document_id = Column(String(64), nullable=True, index=True)
    topic = Column(String(256), nullable=False, index=True)
    subtopic = Column(String(256), nullable=True)
    relevance_score = Column(Float, default=0.5)
    keywords = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_topics_topic", "topic"),
        Index("idx_topics_document", "document_id"),
    )


class CompiledEntityRelation(BaseModel):
    """
    Entity relationship extracted from text.
    Enables graph-style queries without LLM.
    """
    __tablename__ = "compiled_entity_relations"

    entity_a = Column(String(256), nullable=False, index=True)
    relation = Column(String(128), nullable=False, index=True)
    entity_b = Column(String(256), nullable=False, index=True)

    confidence = Column(Float, default=0.5)
    source_text = Column(Text, nullable=True)
    source_document_id = Column(String(64), nullable=True)
    domain = Column(String(128), nullable=True)

    __table_args__ = (
        Index("idx_entities_a", "entity_a"),
        Index("idx_entities_b", "entity_b"),
        Index("idx_entities_relation", "relation"),
    )


# ======================================================================
# KNOWLEDGE COMPILER
# ======================================================================

class KnowledgeCompiler:
    """
    Compiles raw data into deterministic structures using LLM ONCE.

    After compilation, Grace queries the structures without needing
    any LLM. The LLM is a tool used during compilation only.

    Usage:
        compiler = KnowledgeCompiler(session)

        # Compile a single chunk (uses LLM once)
        results = compiler.compile_chunk(text, source_id, domain)

        # Compile all uncompiled chunks in batch
        stats = compiler.compile_batch(limit=100)

        # Query compiled knowledge (NO LLM needed)
        facts = compiler.query_facts(subject="Python")
        procedures = compiler.query_procedures(domain="docker")
        rules = compiler.query_rules(domain="deployment")
    """

    def __init__(self, session: Session, llm_client=None):
        self.session = session
        self.llm_client = llm_client
        self._compilation_count = 0
        logger.info("[COMPILER] Knowledge compiler initialized")

    def compile_chunk(
        self,
        text: str,
        source_document_id: Optional[str] = None,
        source_chunk_id: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compile a single text chunk into structured knowledge.

        Uses the LLM ONCE to extract facts, procedures, rules,
        topics, and entities. Stores everything in SQL tables
        that Grace can query deterministically forever after.
        """
        results = {
            "facts": [],
            "procedures": [],
            "rules": [],
            "topics": [],
            "entities": [],
        }

        # STEP 1: Extract facts, procedures, rules using LLM (ONE CALL)
        if self.llm_client:
            extracted = self._llm_extract(text, domain)
        else:
            extracted = self._heuristic_extract(text, domain)

        # STEP 2: Store extracted knowledge in deterministic tables
        for fact in extracted.get("facts", []):
            compiled = CompiledFact(
                subject=fact.get("subject", ""),
                predicate=fact.get("predicate", ""),
                object_value=str(fact.get("object", "")),
                object_type=fact.get("type", "text"),
                confidence=fact.get("confidence", 0.5),
                source_document_id=source_document_id,
                source_chunk_id=source_chunk_id,
                source_text=text[:500],
                domain=domain,
                tags=fact.get("tags"),
            )
            self.session.add(compiled)
            results["facts"].append(fact)

        for proc in extracted.get("procedures", []):
            compiled = CompiledProcedure(
                name=proc.get("name", f"procedure_{uuid.uuid4().hex[:8]}"),
                goal=proc.get("goal", ""),
                domain=domain,
                trigger_condition=proc.get("trigger", ""),
                steps=proc.get("steps", []),
                preconditions=proc.get("preconditions"),
                expected_outcome=proc.get("expected_outcome", ""),
                confidence=proc.get("confidence", 0.5),
                source_document_id=source_document_id,
            )
            self.session.add(compiled)
            results["procedures"].append(proc)

        for rule in extracted.get("rules", []):
            # Ensure all fields are strings/JSON-serializable (LLM may return dicts)
            alt = rule.get("alternative")
            if isinstance(alt, dict):
                alt = json.dumps(alt)
            expl = rule.get("explanation", "")
            if isinstance(expl, dict):
                expl = json.dumps(expl)
            action = rule.get("action", "")
            if isinstance(action, dict):
                action = json.dumps(action)

            compiled = CompiledDecisionRule(
                rule_name=str(rule.get("name", f"rule_{uuid.uuid4().hex[:8]}"))[:256],
                domain=domain,
                conditions=rule.get("conditions", []),
                action=str(action)[:2000],
                alternative=str(alt) if alt else None,
                explanation=str(expl)[:2000],
                confidence=rule.get("confidence", 0.5),
                source_document_id=source_document_id,
            )
            self.session.add(compiled)
            results["rules"].append(rule)

        for topic in extracted.get("topics", []):
            compiled = CompiledTopicIndex(
                chunk_id=source_chunk_id,
                document_id=source_document_id,
                topic=topic.get("topic", "general"),
                subtopic=topic.get("subtopic"),
                relevance_score=topic.get("relevance", 0.5),
                keywords=topic.get("keywords"),
            )
            self.session.add(compiled)
            results["topics"].append(topic)

        for entity in extracted.get("entities", []):
            compiled = CompiledEntityRelation(
                entity_a=entity.get("entity_a", ""),
                relation=entity.get("relation", ""),
                entity_b=entity.get("entity_b", ""),
                confidence=entity.get("confidence", 0.5),
                source_text=text[:200],
                source_document_id=source_document_id,
                domain=domain,
            )
            self.session.add(compiled)
            results["entities"].append(entity)

        self.session.flush()
        self._compilation_count += 1

        try:
            from cognitive.timesense import get_timesense
            get_timesense().record_operation("knowledge.compile", 1, "knowledge_compiler")
        except Exception:
            pass

        return results

    def _llm_extract(self, text: str, domain: Optional[str]) -> Dict[str, Any]:
        """
        Use LLM to extract structured knowledge from text.

        This is the ONE TIME we use the LLM for this chunk.
        After extraction, Grace never needs the LLM for this data again.
        """
        extraction_prompt = f"""Extract structured knowledge from this text.

TEXT:
{text[:3000]}

Return JSON with these categories:
{{
  "facts": [{{"subject": "X", "predicate": "Y", "object": "Z", "type": "text|number|boolean", "confidence": 0.8}}],
  "procedures": [{{"name": "...", "goal": "...", "steps": [{{"step": 1, "action": "...", "detail": "..."}}], "trigger": "when to use this"}}],
  "rules": [{{"name": "...", "conditions": [{{"field": "...", "operator": "==", "value": "..."}}], "action": "...", "alternative": "...", "explanation": "..."}}],
  "topics": [{{"topic": "main topic", "subtopic": "specific area", "keywords": ["key1", "key2"]}}],
  "entities": [{{"entity_a": "X", "relation": "relates_to", "entity_b": "Y"}}]
}}

Only extract what's explicitly stated. Don't invent facts. Return valid JSON only."""

        try:
            response = self.llm_client.generate(
                prompt=extraction_prompt,
                task_type="reasoning",
                system_prompt="You extract structured facts from text. Output ONLY valid JSON."
            )

            if response.get("success"):
                content = response.get("content", "{}")
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"[COMPILER] LLM extraction failed: {e}")

        # Fallback to heuristic extraction
        return self._heuristic_extract(text, domain)

    def _heuristic_extract(self, text: str, domain: Optional[str]) -> Dict[str, Any]:
        """
        Extract knowledge using heuristic rules (no LLM needed).

        Simpler but works without any LLM. Extracts:
        - Definitions (X is Y patterns)
        - Steps (numbered lists, bullet points with verbs)
        - Conditionals (if/when/should patterns)
        - Topics (common nouns, capitalized terms)
        - Relations (X uses/requires/depends on Y)
        """
        import re
        results = {"facts": [], "procedures": [], "rules": [], "topics": [], "entities": []}

        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            s = sentence.strip()
            if len(s) < 10:
                continue

            # Extract facts: "X is Y" patterns
            is_match = re.match(
                r'^([A-Z][a-zA-Z0-9_ ]{2,30})\s+(?:is|are|was|were)\s+(.{10,200})',
                s
            )
            if is_match:
                results["facts"].append({
                    "subject": is_match.group(1).strip(),
                    "predicate": "is",
                    "object": is_match.group(2).strip().rstrip('.'),
                    "type": "text",
                    "confidence": 0.6,
                })

            # Extract facts: "X = Y" or "X: Y" in definition style
            def_match = re.match(r'^([A-Za-z_]+)\s*[:=]\s*(.{3,100})$', s)
            if def_match:
                results["facts"].append({
                    "subject": def_match.group(1).strip(),
                    "predicate": "equals",
                    "object": def_match.group(2).strip(),
                    "type": "text",
                    "confidence": 0.7,
                })

            # Extract rules: "if X then Y" patterns
            if_match = re.match(
                r'(?:if|when|whenever)\s+(.{10,200}),?\s+(?:then|you should|do|use)\s+(.{5,200})',
                s, re.IGNORECASE
            )
            if if_match:
                results["rules"].append({
                    "name": f"rule_{hashlib.md5(s.encode()).hexdigest()[:8]}",
                    "conditions": [{"field": "context", "operator": "matches", "value": if_match.group(1).strip()}],
                    "action": if_match.group(2).strip().rstrip('.'),
                    "confidence": 0.5,
                })

            # Extract entities: "X uses/requires/depends on Y"
            rel_match = re.match(
                r'([A-Z][a-zA-Z0-9_ ]{2,30})\s+(uses|requires|depends on|extends|implements|contains|supports|integrates with)\s+([A-Z][a-zA-Z0-9_ ]{2,30})',
                s
            )
            if rel_match:
                results["entities"].append({
                    "entity_a": rel_match.group(1).strip(),
                    "relation": rel_match.group(2).strip(),
                    "entity_b": rel_match.group(3).strip(),
                    "confidence": 0.6,
                })

        # Extract topics from the whole text
        words = re.findall(r'\b([A-Z][a-zA-Z]{3,})\b', text)
        if words:
            from collections import Counter
            top_words = Counter(words).most_common(5)
            for word, count in top_words:
                if count >= 2:
                    results["topics"].append({
                        "topic": word,
                        "relevance": min(1.0, count / 10),
                        "keywords": [w for w, _ in top_words[:3]],
                    })

        # Extract procedures from numbered lists
        numbered_steps = re.findall(r'(\d+)[.)\s]+([A-Z].*?)(?=\d+[.)\s]|$)', text, re.DOTALL)
        if len(numbered_steps) >= 2:
            steps = [{"step": int(n), "action": step.strip()[:200]} for n, step in numbered_steps]
            results["procedures"].append({
                "name": f"procedure_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}",
                "goal": sentences[0][:200] if sentences else "Extracted procedure",
                "steps": steps,
                "confidence": 0.5,
            })

        return results

    # ==================================================================
    # DETERMINISTIC QUERIES (NO LLM NEEDED)
    # ==================================================================

    def query_facts(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        domain: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query compiled facts. Pure SQL lookup, no LLM."""
        query = self.session.query(CompiledFact)

        if subject:
            query = query.filter(CompiledFact.subject.ilike(f"%{subject}%"))
        if predicate:
            query = query.filter(CompiledFact.predicate.ilike(f"%{predicate}%"))
        if domain:
            query = query.filter(CompiledFact.domain == domain)
        if min_confidence > 0:
            query = query.filter(CompiledFact.confidence >= min_confidence)

        query = query.order_by(CompiledFact.confidence.desc()).limit(limit)

        facts = query.all()

        for fact in facts:
            fact.times_accessed += 1

        if facts:
            self.session.flush()

        return [
            {
                "subject": f.subject,
                "predicate": f.predicate,
                "object": f.object_value,
                "type": f.object_type,
                "confidence": f.confidence,
                "domain": f.domain,
                "verified": f.verified,
            }
            for f in facts
        ]

    def query_procedures(
        self,
        goal: Optional[str] = None,
        domain: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Query compiled procedures. Pure SQL lookup, no LLM."""
        query = self.session.query(CompiledProcedure)

        if goal:
            query = query.filter(CompiledProcedure.goal.ilike(f"%{goal}%"))
        if domain:
            query = query.filter(CompiledProcedure.domain == domain)
        if min_confidence > 0:
            query = query.filter(CompiledProcedure.confidence >= min_confidence)

        query = query.order_by(CompiledProcedure.confidence.desc()).limit(limit)

        return [
            {
                "name": p.name,
                "goal": p.goal,
                "steps": p.steps,
                "preconditions": p.preconditions,
                "expected_outcome": p.expected_outcome,
                "confidence": p.confidence,
                "success_rate": p.success_rate,
                "domain": p.domain,
            }
            for p in query.all()
        ]

    def query_rules(
        self,
        domain: Optional[str] = None,
        context: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Query compiled decision rules. Pure SQL lookup, no LLM."""
        query = self.session.query(CompiledDecisionRule)

        if domain:
            query = query.filter(CompiledDecisionRule.domain == domain)

        query = query.order_by(CompiledDecisionRule.confidence.desc()).limit(limit)

        rules = query.all()

        if context:
            matched = []
            for rule in rules:
                conditions = rule.conditions or []
                for cond in conditions:
                    if cond.get("value", "").lower() in context.lower():
                        matched.append(rule)
                        break
            rules = matched if matched else rules

        return [
            {
                "rule_name": r.rule_name,
                "conditions": r.conditions,
                "action": r.action,
                "alternative": r.alternative,
                "explanation": r.explanation,
                "confidence": r.confidence,
                "domain": r.domain,
            }
            for r in rules
        ]

    def query_topics(
        self,
        topic: Optional[str] = None,
        document_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query topic index. Pure SQL lookup, no LLM."""
        query = self.session.query(CompiledTopicIndex)

        if topic:
            query = query.filter(CompiledTopicIndex.topic.ilike(f"%{topic}%"))
        if document_id:
            query = query.filter(CompiledTopicIndex.document_id == document_id)

        query = query.order_by(CompiledTopicIndex.relevance_score.desc()).limit(limit)

        return [
            {
                "topic": t.topic,
                "subtopic": t.subtopic,
                "relevance": t.relevance_score,
                "keywords": t.keywords,
                "document_id": t.document_id,
                "chunk_id": t.chunk_id,
            }
            for t in query.all()
        ]

    def query_entities(
        self,
        entity: Optional[str] = None,
        relation: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query entity relationships. Pure SQL lookup, no LLM."""
        query = self.session.query(CompiledEntityRelation)

        if entity:
            query = query.filter(
                (CompiledEntityRelation.entity_a.ilike(f"%{entity}%")) |
                (CompiledEntityRelation.entity_b.ilike(f"%{entity}%"))
            )
        if relation:
            query = query.filter(CompiledEntityRelation.relation == relation)
        if domain:
            query = query.filter(CompiledEntityRelation.domain == domain)

        query = query.order_by(CompiledEntityRelation.confidence.desc()).limit(limit)

        return [
            {
                "entity_a": e.entity_a,
                "relation": e.relation,
                "entity_b": e.entity_b,
                "confidence": e.confidence,
                "domain": e.domain,
            }
            for e in query.all()
        ]

    def compile_batch(self, limit: int = 100) -> Dict[str, Any]:
        """
        Compile a batch of uncompiled document chunks.

        Finds chunks that haven't been compiled yet and processes them.
        """
        try:
            from models.database_models import DocumentChunk

            # Find chunks not yet compiled (no matching topic index entry)
            compiled_chunks = set(
                r[0] for r in self.session.query(CompiledTopicIndex.chunk_id).all()
                if r[0]
            )

            chunks = self.session.query(DocumentChunk).limit(limit + len(compiled_chunks)).all()
            uncompiled = [c for c in chunks if str(c.id) not in compiled_chunks][:limit]

            stats = {"processed": 0, "facts": 0, "procedures": 0, "rules": 0, "topics": 0, "entities": 0}

            for chunk in uncompiled:
                text = chunk.text_content
                if not text or len(text) < 20:
                    continue

                results = self.compile_chunk(
                    text=text,
                    source_document_id=str(chunk.document_id),
                    source_chunk_id=str(chunk.id),
                    domain=None,
                )

                stats["processed"] += 1
                stats["facts"] += len(results.get("facts", []))
                stats["procedures"] += len(results.get("procedures", []))
                stats["rules"] += len(results.get("rules", []))
                stats["topics"] += len(results.get("topics", []))
                stats["entities"] += len(results.get("entities", []))

            self.session.commit()

            logger.info(
                f"[COMPILER] Batch complete: {stats['processed']} chunks, "
                f"{stats['facts']} facts, {stats['procedures']} procedures, "
                f"{stats['rules']} rules, {stats['topics']} topics, "
                f"{stats['entities']} entities"
            )

            return stats

        except Exception as e:
            logger.error(f"[COMPILER] Batch compilation error: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get compilation statistics."""
        try:
            return {
                "total_facts": self.session.query(CompiledFact).count(),
                "total_procedures": self.session.query(CompiledProcedure).count(),
                "total_rules": self.session.query(CompiledDecisionRule).count(),
                "total_topics": self.session.query(CompiledTopicIndex).count(),
                "total_entities": self.session.query(CompiledEntityRelation).count(),
                "compilations_this_session": self._compilation_count,
            }
        except Exception:
            return {"compilations_this_session": self._compilation_count}


# ======================================================================
# LLM KNOWLEDGE DISTILLATION MODEL
# ======================================================================

class DistilledKnowledge(BaseModel):
    """
    Knowledge extracted directly from the LLM's weights.

    Every time we ask the LLM a question, the INPUT and OUTPUT
    are stored together. Over time, this builds a distilled copy
    of the LLM's knowledge in deterministic SQL.

    The LLM's weights encode: input -> output mappings.
    We capture those mappings explicitly so Grace can replay
    them without the LLM.
    """
    __tablename__ = "distilled_knowledge"

    query_hash = Column(String(64), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(64), nullable=True, index=True)
    query_domain = Column(String(128), nullable=True, index=True)

    response_text = Column(Text, nullable=False)
    response_structured = Column(JSON, nullable=True)

    model_used = Column(String(128), nullable=True)
    confidence = Column(Float, default=0.5)
    quality_score = Column(Float, nullable=True)

    times_accessed = Column(Integer, default=0)
    times_validated = Column(Integer, default=0)
    times_invalidated = Column(Integer, default=0)

    user_feedback = Column(String(32), nullable=True)
    is_verified = Column(Boolean, default=False)

    __table_args__ = (
        Index("idx_distilled_hash", "query_hash"),
        Index("idx_distilled_domain", "query_domain"),
        Index("idx_distilled_type", "query_type"),
    )


class LLMKnowledgeMiner:
    """
    Mines the LLM systematically to extract its knowledge into
    deterministic storage.

    The LLM has knowledge in its weights. We can't read the weights
    directly, but we CAN:
    1. Ask it questions systematically
    2. Store every input/output pair
    3. Build a lookup table: query -> answer
    4. Over time, Grace checks the lookup BEFORE calling the LLM
    5. If the answer is already stored with high confidence, skip the LLM

    This is knowledge distillation through usage:
    - Every user question that goes through the LLM gets stored
    - Every LLM response gets stored with the query
    - Proactive mining asks the LLM about known topics to pre-fill
    - Quality scoring from user feedback improves stored answers
    - Eventually: Grace answers from the distilled store, not the LLM
    """

    def __init__(self, session: Session, llm_client=None):
        self.session = session
        self.llm_client = llm_client
        self._mine_count = 0

    def store_interaction(
        self,
        query: str,
        response: str,
        model_used: str = "unknown",
        query_type: Optional[str] = None,
        domain: Optional[str] = None,
        confidence: float = 0.5,
        structured_response: Optional[Dict[str, Any]] = None,
    ) -> DistilledKnowledge:
        """
        Store an LLM interaction as distilled knowledge.

        Called automatically from the /chat pipeline for every
        LLM call. Builds the lookup table over time.
        """
        query_hash = hashlib.sha256(query.strip().lower().encode()).hexdigest()[:16]

        existing = self.session.query(DistilledKnowledge).filter(
            DistilledKnowledge.query_hash == query_hash
        ).first()

        if existing:
            existing.times_accessed += 1
            if confidence > existing.confidence:
                existing.response_text = response
                existing.confidence = confidence
                existing.model_used = model_used
                if structured_response:
                    existing.response_structured = structured_response
            self.session.flush()
            return existing

        entry = DistilledKnowledge(
            query_hash=query_hash,
            query_text=query[:5000],
            query_type=query_type,
            query_domain=domain,
            response_text=response[:10000],
            response_structured=structured_response,
            model_used=model_used,
            confidence=confidence,
        )
        self.session.add(entry)
        self.session.flush()

        return entry

    def lookup(
        self,
        query: str,
        min_confidence: float = 0.7,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a query in distilled knowledge BEFORE calling the LLM.

        If a high-confidence answer exists, return it.
        Grace can use this to skip the LLM entirely.

        Returns:
            Dict with response if found and confident, None otherwise
        """
        query_hash = hashlib.sha256(query.strip().lower().encode()).hexdigest()[:16]

        entry = self.session.query(DistilledKnowledge).filter(
            DistilledKnowledge.query_hash == query_hash,
            DistilledKnowledge.confidence >= min_confidence,
        ).first()

        if entry:
            entry.times_accessed += 1
            self.session.flush()

            return {
                "response": entry.response_text,
                "structured": entry.response_structured,
                "confidence": entry.confidence,
                "model_used": entry.model_used,
                "times_accessed": entry.times_accessed,
                "verified": entry.is_verified,
                "source": "distilled_knowledge",
            }

        return None

    def fuzzy_lookup(
        self,
        query: str,
        min_confidence: float = 0.6,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fuzzy lookup using SQL LIKE matching on query text.

        Less precise than hash lookup but catches rephrased questions.
        """
        keywords = [w for w in query.lower().split() if len(w) > 3][:5]

        if not keywords:
            return []

        results = self.session.query(DistilledKnowledge).filter(
            DistilledKnowledge.confidence >= min_confidence
        )

        for keyword in keywords[:2]:
            results = results.filter(
                DistilledKnowledge.query_text.ilike(f"%{keyword}%")
            )

        results = results.order_by(
            DistilledKnowledge.confidence.desc()
        ).limit(limit).all()

        return [
            {
                "query": r.query_text[:200],
                "response": r.response_text[:500],
                "confidence": r.confidence,
                "verified": r.is_verified,
                "times_accessed": r.times_accessed,
            }
            for r in results
        ]

    def mine_topic(
        self,
        topic: str,
        questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Proactively mine the LLM about a topic.

        Generates questions about the topic and stores all answers.
        This pre-fills the distilled knowledge store so Grace can
        answer these questions later without calling the LLM.
        """
        if not self.llm_client:
            return {"error": "No LLM client available for mining"}

        if not questions:
            questions = [
                f"What is {topic}?",
                f"How does {topic} work?",
                f"What are the key concepts of {topic}?",
                f"What are common problems with {topic}?",
                f"What are best practices for {topic}?",
                f"How do you configure {topic}?",
                f"What are alternatives to {topic}?",
            ]

        mined = 0
        for question in questions:
            try:
                response = self.llm_client.generate(
                    prompt=question,
                    task_type="reasoning",
                    system_prompt="Give a clear, factual answer. Be specific and concise."
                )

                if response.get("success"):
                    content = response.get("content", "")
                    self.store_interaction(
                        query=question,
                        response=content,
                        model_used=response.get("model_name", "unknown"),
                        domain=topic.lower(),
                        confidence=0.7,
                    )
                    mined += 1

            except Exception as e:
                logger.warning(f"[MINER] Failed to mine '{question}': {e}")

        self.session.commit()
        self._mine_count += mined

        logger.info(f"[MINER] Mined {mined}/{len(questions)} answers about '{topic}'")

        return {
            "topic": topic,
            "questions_asked": len(questions),
            "answers_stored": mined,
        }

    def update_quality(
        self,
        query: str,
        feedback: str,
        quality_score: Optional[float] = None,
    ):
        """
        Update quality of distilled knowledge based on feedback.

        When a user upvotes/downvotes a response, this updates the
        confidence of the stored knowledge.
        """
        query_hash = hashlib.sha256(query.strip().lower().encode()).hexdigest()[:16]

        entry = self.session.query(DistilledKnowledge).filter(
            DistilledKnowledge.query_hash == query_hash
        ).first()

        if not entry:
            return

        entry.user_feedback = feedback

        if feedback == "positive":
            entry.times_validated += 1
            entry.confidence = min(1.0, entry.confidence * 1.1)
            if entry.times_validated >= 3:
                entry.is_verified = True
        elif feedback == "negative":
            entry.times_invalidated += 1
            entry.confidence = max(0.0, entry.confidence * 0.7)
            entry.is_verified = False

        if quality_score is not None:
            entry.quality_score = quality_score

        self.session.flush()

    def get_stats(self) -> Dict[str, Any]:
        """Get distillation statistics."""
        try:
            total = self.session.query(DistilledKnowledge).count()
            verified = self.session.query(DistilledKnowledge).filter(
                DistilledKnowledge.is_verified == True
            ).count()
            high_conf = self.session.query(DistilledKnowledge).filter(
                DistilledKnowledge.confidence >= 0.7
            ).count()

            return {
                "total_distilled": total,
                "verified": verified,
                "high_confidence": high_conf,
                "verification_rate": verified / total if total > 0 else 0,
                "coverage_rate": high_conf / total if total > 0 else 0,
                "mined_this_session": self._mine_count,
            }
        except Exception:
            return {"mined_this_session": self._mine_count}


_miner_instance: Optional[LLMKnowledgeMiner] = None


def get_llm_knowledge_miner(session: Session, llm_client=None) -> LLMKnowledgeMiner:
    """Get or create the LLM knowledge miner singleton."""
    global _miner_instance
    if _miner_instance is None:
        _miner_instance = LLMKnowledgeMiner(session, llm_client)
    return _miner_instance


_compiler_instance: Optional[KnowledgeCompiler] = None


def get_knowledge_compiler(session: Session, llm_client=None) -> KnowledgeCompiler:
    """Get or create the knowledge compiler singleton."""
    global _compiler_instance
    if _compiler_instance is None:
        _compiler_instance = KnowledgeCompiler(session, llm_client)
    return _compiler_instance
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
# Appended KnowledgeIndexer and RetrievalQualityTracker
