"""
Socratic Interrogation Engine

Before Grace trusts ANY document, she interrogates it with a structured
checklist of 6W questions -- just like a human analyst would:

  WHAT does this document do?
  HOW does this work?
  WHO created it / where does it go to?
  WHERE does this fit in the system?
  WHY do I need it?
  WHEN do I need it?

This creates a Genesis Key at the interrogation stage. The answers become
structured metadata that travels with the document through the entire
pipeline. The LLM generates the answers, then the Source Code Index and
Oracle verify them back against reality.

Two verification loops:
  1. LLM answers questions → Source Code Index verifies → confirmed/refuted
  2. LLM answers questions → Oracle cross-checks → confirmed/refuted

After interrogation, Grace asks the Oracle: "Based on what you've seen,
is there anything ELSE I need that I don't have?" This generates gap
discovery queries that feed back into the perpetual learning loop.

Communication format:
  Grace-to-Grace: JSON (structured, parseable, fast)
  Grace-to-LLM:   NLP (natural language prompts, human-readable)
"""

import logging
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .source_code_index import SourceCodeIndex
from .oracle_vector_store import OracleVectorStore

logger = logging.getLogger(__name__)


class QuestionCategory(str, Enum):
    """The 6W interrogation categories."""
    WHAT = "what"
    HOW = "how"
    WHO = "who"
    WHERE = "where"
    WHY = "why"
    WHEN = "when"


class AnswerConfidence(str, Enum):
    """Confidence in an answer."""
    VERIFIED = "verified"            # Confirmed by source code or Oracle
    LIKELY = "likely"                # Partially confirmed
    UNCERTAIN = "uncertain"          # Could not confirm
    CONTRADICTED = "contradicted"    # Evidence contradicts this answer


class CommunicationFormat(str, Enum):
    """Format for inter-system communication."""
    JSON = "json"     # Grace-to-Grace: structured, machine-parseable
    NLP = "nlp"       # Grace-to-LLM: natural language, human-readable


@dataclass
class InterrogationQuestion:
    """A single interrogation question."""
    question_id: str
    category: QuestionCategory
    question_text: str
    # NLP version (for LLM)
    nlp_prompt: str
    # JSON version (for internal systems)
    json_query: Dict[str, Any]


@dataclass
class InterrogationAnswer:
    """An answer to an interrogation question."""
    question_id: str
    category: QuestionCategory
    answer_text: str
    confidence: AnswerConfidence
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    source_verified: bool = False
    oracle_verified: bool = False
    verification_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InterrogationReport:
    """Complete interrogation report for a document."""
    report_id: str
    document_id: str
    document_content_preview: str
    questions_asked: int
    answers_verified: int
    answers_contradicted: int
    answers: List[InterrogationAnswer]
    overall_confidence: float
    is_useful: bool
    gap_queries: List[str]  # Additional queries to fill gaps
    genesis_key_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON for Grace-to-Grace communication."""
        return {
            "report_id": self.report_id,
            "document_id": self.document_id,
            "questions_asked": self.questions_asked,
            "answers_verified": self.answers_verified,
            "answers_contradicted": self.answers_contradicted,
            "overall_confidence": self.overall_confidence,
            "is_useful": self.is_useful,
            "gap_queries": self.gap_queries,
            "genesis_key": self.genesis_key_data,
            "answers": [
                {
                    "category": a.category.value,
                    "answer": a.answer_text,
                    "confidence": a.confidence.value,
                    "source_verified": a.source_verified,
                    "oracle_verified": a.oracle_verified,
                }
                for a in self.answers
            ],
            "timestamp": self.timestamp.isoformat(),
        }

    def to_nlp(self) -> str:
        """Convert to NLP for Grace-to-LLM communication."""
        lines = [
            f"Document Interrogation Report: {self.document_id}",
            f"Overall confidence: {self.overall_confidence:.0%}",
            f"Useful to system: {'Yes' if self.is_useful else 'No'}",
            "",
        ]
        for a in self.answers:
            verified = ""
            if a.source_verified:
                verified += " [source-verified]"
            if a.oracle_verified:
                verified += " [oracle-verified]"
            lines.append(f"{a.category.value.upper()}: {a.answer_text}{verified}")
        if self.gap_queries:
            lines.append("")
            lines.append("Additional knowledge needed:")
            for gq in self.gap_queries:
                lines.append(f"  - {gq}")
        return "\n".join(lines)


class SocraticInterrogator:
    """
    Grace's Socratic questioning engine for document analysis.

    Every document that enters the system gets interrogated with
    structured 6W questions. Answers are generated by LLM (NLP format),
    then verified against Source Code Index and Oracle (JSON format).

    The interrogation creates a Genesis Key at the questioning stage,
    and the structured answers become permanent metadata.

    After interrogation, the engine asks the Oracle:
    "Is there anything else I need that I don't have?"
    This generates gap discovery queries for the perpetual loop.

    Dual-format communication:
    - JSON: Grace-to-Grace (internal, structured, fast)
    - NLP: Grace-to-LLM (natural language, flexible)
    """

    # The 6W question templates
    QUESTION_TEMPLATES = {
        QuestionCategory.WHAT: {
            "template": "What does this document do? What is its purpose?",
            "nlp_prompt": (
                "Analyze the following content and answer: "
                "What does this document do? What is its primary purpose? "
                "What problem does it solve?\n\nContent:\n{content}"
            ),
            "json_query": {
                "action": "analyze_purpose",
                "extract": ["purpose", "function", "output"],
            },
        },
        QuestionCategory.HOW: {
            "template": "How does this work? What is the mechanism?",
            "nlp_prompt": (
                "Analyze the following content and answer: "
                "How does this work? What are the key mechanisms, "
                "algorithms, or processes involved?\n\nContent:\n{content}"
            ),
            "json_query": {
                "action": "analyze_mechanism",
                "extract": ["mechanism", "algorithm", "process", "steps"],
            },
        },
        QuestionCategory.WHO: {
            "template": "Who created this? Who uses it? Where does it go?",
            "nlp_prompt": (
                "Analyze the following content and answer: "
                "Who created this? Who is the intended audience? "
                "What system or person does it connect to?\n\nContent:\n{content}"
            ),
            "json_query": {
                "action": "analyze_actors",
                "extract": ["creator", "audience", "connections"],
            },
        },
        QuestionCategory.WHERE: {
            "template": "Where does this fit in the system? What depends on it?",
            "nlp_prompt": (
                "Analyze the following content and answer: "
                "Where does this fit in the system architecture? "
                "What components depend on it? What does it depend on?\n\nContent:\n{content}"
            ),
            "json_query": {
                "action": "analyze_position",
                "extract": ["location", "dependencies", "dependents"],
            },
        },
        QuestionCategory.WHY: {
            "template": "Why do I need this? What value does it add?",
            "nlp_prompt": (
                "Analyze the following content and answer: "
                "Why is this needed? What value does it add to the system? "
                "What would be missing without it?\n\nContent:\n{content}"
            ),
            "json_query": {
                "action": "analyze_value",
                "extract": ["value", "necessity", "impact_if_missing"],
            },
        },
        QuestionCategory.WHEN: {
            "template": "When do I need this? Is it time-sensitive?",
            "nlp_prompt": (
                "Analyze the following content and answer: "
                "When is this needed? Is it time-sensitive? "
                "Is it current or outdated?\n\nContent:\n{content}"
            ),
            "json_query": {
                "action": "analyze_timing",
                "extract": ["timing", "urgency", "freshness", "expiry"],
            },
        },
    }

    def __init__(
        self,
        source_index: Optional[SourceCodeIndex] = None,
        oracle_store: Optional[OracleVectorStore] = None,
    ):
        self.source_index = source_index or SourceCodeIndex()
        self.oracle_store = oracle_store
        self._llm_handler = None
        self.reports: List[InterrogationReport] = []
        logger.info("[SOCRATIC] Interrogation Engine initialized")

    def set_llm_handler(self, handler) -> None:
        """Set the LLM handler for generating answers."""
        self._llm_handler = handler

    def interrogate(
        self, content: str, document_id: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> InterrogationReport:
        """
        Interrogate a document with the full 6W question battery.

        1. Generate questions (JSON + NLP format)
        2. Get answers from LLM (NLP) or heuristic analysis
        3. Verify answers against Source Code Index
        4. Verify answers against Oracle
        5. Ask Oracle for gaps
        6. Generate Genesis Key data
        7. Return structured report (JSON for Grace, NLP for LLM)

        Args:
            content: Document content to interrogate
            document_id: Optional document ID
            domain: Optional domain hint

        Returns:
            InterrogationReport
        """
        if not document_id:
            document_id = f"doc-{hashlib.sha256(content.encode()).hexdigest()[:12]}"

        questions = self._generate_questions(content)
        answers: List[InterrogationAnswer] = []

        for question in questions:
            # Get answer (LLM or heuristic)
            answer_text = self._get_answer(question, content)

            # Verify against source code
            source_verified, source_evidence = self._verify_against_source(
                answer_text, question.category
            )

            # Verify against Oracle
            oracle_verified, oracle_evidence = self._verify_against_oracle(
                answer_text, question.category
            )

            # Determine confidence
            confidence = self._assess_confidence(
                source_verified, oracle_verified
            )

            answer = InterrogationAnswer(
                question_id=question.question_id,
                category=question.category,
                answer_text=answer_text,
                confidence=confidence,
                evidence=source_evidence + oracle_evidence,
                source_verified=source_verified,
                oracle_verified=oracle_verified,
                verification_details={
                    "source_evidence_count": len(source_evidence),
                    "oracle_evidence_count": len(oracle_evidence),
                },
            )
            answers.append(answer)

        # Ask Oracle for gaps
        gap_queries = self._discover_gaps(content, answers, domain)

        # Calculate overall confidence
        verified_count = sum(
            1 for a in answers
            if a.confidence in (AnswerConfidence.VERIFIED, AnswerConfidence.LIKELY)
        )
        contradicted_count = sum(
            1 for a in answers if a.confidence == AnswerConfidence.CONTRADICTED
        )
        total = len(answers)
        overall_confidence = verified_count / max(total, 1)

        # Determine usefulness
        is_useful = overall_confidence >= 0.3 and contradicted_count < total / 2

        # Genesis Key data
        genesis_key_data = {
            "key_type": "document_interrogation",
            "what_description": f"Interrogated document {document_id}",
            "who_actor": "socratic_interrogator",
            "where_location": f"domain:{domain}" if domain else "unknown",
            "why_reason": "Structured analysis before ingestion",
            "how_method": "6W Socratic questioning with dual verification",
            "when_timestamp": datetime.now(timezone.utc).isoformat(),
            "context_data": {
                "questions_asked": total,
                "verified": verified_count,
                "contradicted": contradicted_count,
                "overall_confidence": overall_confidence,
                "is_useful": is_useful,
                "gap_queries": gap_queries,
            },
        }

        report = InterrogationReport(
            report_id=f"interrog-{uuid.uuid4().hex[:12]}",
            document_id=document_id,
            document_content_preview=content[:200],
            questions_asked=total,
            answers_verified=verified_count,
            answers_contradicted=contradicted_count,
            answers=answers,
            overall_confidence=overall_confidence,
            is_useful=is_useful,
            gap_queries=gap_queries,
            genesis_key_data=genesis_key_data,
        )

        self.reports.append(report)

        logger.info(
            f"[SOCRATIC] Interrogated {document_id}: "
            f"{verified_count}/{total} verified, "
            f"confidence={overall_confidence:.0%}, "
            f"useful={is_useful}, "
            f"{len(gap_queries)} gap queries"
        )

        return report

    def _generate_questions(self, content: str) -> List[InterrogationQuestion]:
        """Generate 6W questions for the content."""
        questions: List[InterrogationQuestion] = []
        for category, template in self.QUESTION_TEMPLATES.items():
            questions.append(InterrogationQuestion(
                question_id=f"q-{uuid.uuid4().hex[:8]}",
                category=category,
                question_text=template["template"],
                nlp_prompt=template["nlp_prompt"].format(content=content[:1500]),
                json_query={
                    **template["json_query"],
                    "content_hash": hashlib.sha256(content.encode()).hexdigest()[:12],
                },
            ))
        return questions

    def _get_answer(
        self, question: InterrogationQuestion, content: str
    ) -> str:
        """Get an answer to a question (LLM or heuristic)."""
        if self._llm_handler:
            try:
                return self._llm_handler(question.nlp_prompt)
            except Exception as e:
                logger.warning(f"[SOCRATIC] LLM handler failed: {e}")

        # Heuristic analysis when LLM not available
        return self._heuristic_answer(question.category, content)

    def _heuristic_answer(
        self, category: QuestionCategory, content: str
    ) -> str:
        """Generate heuristic answers from content analysis."""
        content_lower = content.lower()
        word_count = len(content.split())
        has_code = any(kw in content for kw in ["def ", "class ", "import ", "function "])
        has_urls = "http" in content_lower

        if category == QuestionCategory.WHAT:
            if has_code:
                # Extract first class or function name
                for kw in ["class ", "def "]:
                    if kw in content:
                        idx = content.index(kw) + len(kw)
                        end = content.find("(", idx)
                        if end == -1:
                            end = content.find(":", idx)
                        if end > idx:
                            name = content[idx:end].strip()
                            return f"This document defines '{name}' - a code component with {word_count} words of implementation."
                return f"This document contains code with {word_count} words."
            return f"This document contains {word_count} words of content covering the described topic."

        elif category == QuestionCategory.HOW:
            if has_code:
                return "This works through code implementation with defined functions and classes."
            return "This works through the described concepts and processes in the content."

        elif category == QuestionCategory.WHO:
            if has_code:
                return "Created for developers. Connects to the codebase and related modules."
            return "Created for knowledge consumers. Connects to the document knowledge base."

        elif category == QuestionCategory.WHERE:
            if has_code:
                return "Fits in the codebase as a code module or utility."
            return "Fits in the documents knowledge base for reference and learning."

        elif category == QuestionCategory.WHY:
            return f"Needed to provide knowledge/capability. Contains {word_count} words of relevant content."

        elif category == QuestionCategory.WHEN:
            if any(kw in content_lower for kw in ["deprecated", "legacy", "old version"]):
                return "This content may be outdated. Time-sensitive review recommended."
            return "This content appears current and can be used immediately."

        return "Unable to determine from heuristic analysis alone."

    def _verify_against_source(
        self, answer: str, category: QuestionCategory
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify an answer against the Source Code Index."""
        evidence: List[Dict[str, Any]] = []

        # Extract potential code references from the answer
        words = answer.split()
        code_refs = [w.strip("'\".,()") for w in words if len(w) > 2]

        for ref in code_refs[:5]:
            if self.source_index.what_exists(ref):
                query = self.source_index.query_by_name(ref)
                for elem in query.results[:2]:
                    evidence.append({
                        "source": "source_code_index",
                        "entity": ref,
                        "found": True,
                        "type": elem.element_type.value,
                        "file": elem.file_path,
                    })

        # Also check capability-based
        capability_query = self.source_index.query_by_capability(answer[:100])
        if capability_query.results:
            evidence.append({
                "source": "source_code_capability",
                "matches": len(capability_query.results),
            })

        verified = len(evidence) > 0
        return verified, evidence

    def _verify_against_oracle(
        self, answer: str, category: QuestionCategory
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify an answer against the Oracle knowledge base."""
        evidence: List[Dict[str, Any]] = []

        if not self.oracle_store:
            return False, evidence

        results = self.oracle_store.search_by_content(answer, limit=5)
        for r in results:
            if r.score > 0.15:
                evidence.append({
                    "source": "oracle_store",
                    "content_preview": r.content[:80],
                    "score": r.score,
                    "domain": r.domain,
                    "trust": r.trust_score,
                })

        verified = any(e.get("score", 0) > 0.2 for e in evidence)
        return verified, evidence

    def _assess_confidence(
        self, source_verified: bool, oracle_verified: bool
    ) -> AnswerConfidence:
        """Assess confidence based on verification results."""
        if source_verified and oracle_verified:
            return AnswerConfidence.VERIFIED
        elif source_verified or oracle_verified:
            return AnswerConfidence.LIKELY
        else:
            return AnswerConfidence.UNCERTAIN

    def _discover_gaps(
        self, content: str, answers: List[InterrogationAnswer],
        domain: Optional[str] = None,
    ) -> List[str]:
        """
        Ask the Oracle: "Is there anything else I need?"

        Based on interrogation answers, find knowledge gaps.
        """
        gap_queries: List[str] = []

        # Find uncertain answers - those are gaps
        uncertain = [
            a for a in answers
            if a.confidence in (AnswerConfidence.UNCERTAIN, AnswerConfidence.CONTRADICTED)
        ]

        for answer in uncertain:
            if answer.category == QuestionCategory.HOW:
                gap_queries.append(
                    f"How does the mechanism described in this content actually work? "
                    f"Need detailed explanation."
                )
            elif answer.category == QuestionCategory.WHERE:
                gap_queries.append(
                    f"Where does this component fit in the system architecture? "
                    f"Need integration documentation."
                )
            elif answer.category == QuestionCategory.WHY:
                gap_queries.append(
                    f"Why is this needed? Need justification and use cases."
                )

        # Ask Oracle about related domains
        if self.oracle_store and domain:
            existing_domains = set(self.oracle_store.get_all_domains())
            # Check if related domains are missing
            domain_neighbors = {
                "python": ["testing", "debugging", "packaging"],
                "ai_ml": ["data_preprocessing", "model_evaluation", "deployment"],
                "devops": ["monitoring", "logging", "alerting"],
                "security": ["authentication", "authorization", "audit"],
            }
            related = domain_neighbors.get(domain, [])
            for rel in related:
                if rel not in existing_domains:
                    gap_queries.append(
                        f"Need knowledge about '{rel}' to complement '{domain}' domain."
                    )

        return gap_queries[:5]  # Limit to 5 gap queries

    # =========================================================================
    # DUAL-FORMAT COMMUNICATION
    # =========================================================================

    def format_for_grace(self, report: InterrogationReport) -> Dict[str, Any]:
        """
        Format report as JSON for Grace-to-Grace communication.

        Structured, parseable, fast for internal systems.
        """
        return report.to_json()

    def format_for_llm(self, report: InterrogationReport) -> str:
        """
        Format report as NLP for Grace-to-LLM communication.

        Natural language, human-readable, context-rich.
        """
        return report.to_nlp()

    def create_genesis_key_from_report(
        self, report: InterrogationReport
    ) -> Dict[str, Any]:
        """
        Create a Genesis Key from the interrogation report.

        This key tracks the interrogation itself as an event.
        """
        return {
            **report.genesis_key_data,
            "report_id": report.report_id,
            "document_id": report.document_id,
            "tags": [
                "interrogation",
                "socratic",
                f"confidence_{int(report.overall_confidence * 100)}",
                "useful" if report.is_useful else "not_useful",
            ],
        }

    # =========================================================================
    # BATCH INTERROGATION
    # =========================================================================

    def interrogate_batch(
        self, documents: List[Dict[str, Any]]
    ) -> List[InterrogationReport]:
        """
        Interrogate a batch of documents.

        Args:
            documents: List of dicts with 'content' and optional 'id', 'domain'

        Returns:
            List of InterrogationReport
        """
        reports: List[InterrogationReport] = []
        for doc in documents:
            report = self.interrogate(
                content=doc.get("content", ""),
                document_id=doc.get("id"),
                domain=doc.get("domain"),
            )
            reports.append(report)
        return reports

    def get_all_gap_queries(self) -> List[str]:
        """Get all gap queries from all interrogations."""
        all_gaps: List[str] = []
        seen = set()
        for report in self.reports:
            for gap in report.gap_queries:
                if gap not in seen:
                    all_gaps.append(gap)
                    seen.add(gap)
        return all_gaps

    def get_stats(self) -> Dict[str, Any]:
        """Get interrogation statistics."""
        if not self.reports:
            return {
                "total_interrogations": 0,
                "average_confidence": 0.0,
                "useful_rate": 0.0,
                "total_gap_queries": 0,
            }

        total = len(self.reports)
        avg_conf = sum(r.overall_confidence for r in self.reports) / total
        useful = sum(1 for r in self.reports if r.is_useful)
        total_gaps = sum(len(r.gap_queries) for r in self.reports)

        return {
            "total_interrogations": total,
            "average_confidence": avg_conf,
            "useful_rate": useful / total,
            "total_gap_queries": total_gaps,
            "total_verified": sum(r.answers_verified for r in self.reports),
            "total_contradicted": sum(r.answers_contradicted for r in self.reports),
        }
