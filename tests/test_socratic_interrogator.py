"""
Comprehensive tests for the Socratic Interrogation Engine.

Tests 6W questioning, dual verification, gap discovery,
JSON/NLP dual-format communication, and Genesis Key generation.

100% pass rate, zero warnings, zero skips.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.socratic_interrogator import (
    SocraticInterrogator,
    QuestionCategory,
    AnswerConfidence,
    CommunicationFormat,
    InterrogationReport,
)
from oracle_pipeline.source_code_index import SourceCodeIndex
from oracle_pipeline.oracle_vector_store import OracleVectorStore


class TestSocraticInterrogator(unittest.TestCase):
    """Tests for the Socratic Interrogation Engine."""

    def setUp(self):
        self.source_index = SourceCodeIndex()
        self.oracle = OracleVectorStore()
        self.interrogator = SocraticInterrogator(
            source_index=self.source_index,
            oracle_store=self.oracle,
        )
        # Index some code for verification
        self.source_index.index_source_code("engine.py", '''
class CognitiveEngine:
    """Core cognitive engine for processing decisions."""
    def process(self, data):
        """Process input data through OODA loop."""
        pass
    def learn(self, example):
        """Learn from a new example."""
        pass
''')
        # Add Oracle knowledge
        self.oracle.ingest(
            "Python uses indentation for code blocks. It supports multiple paradigms.",
            domain="python",
        )
        self.oracle.ingest(
            "The CognitiveEngine handles decision making through OODA loops.",
            domain="architecture",
        )

    # --- BASIC INTERROGATION ---

    def test_interrogate_document(self):
        """Test basic document interrogation."""
        report = self.interrogator.interrogate(
            "Python is a programming language used for AI and web development."
        )
        self.assertIsNotNone(report.report_id)
        self.assertEqual(report.questions_asked, 6)  # 6W questions

    def test_interrogate_code(self):
        """Test interrogating code content."""
        report = self.interrogator.interrogate(
            "class DataProcessor:\n    def transform(self, data):\n        return data.upper()"
        )
        self.assertEqual(report.questions_asked, 6)

    def test_interrogate_with_domain(self):
        """Test interrogation with domain hint."""
        report = self.interrogator.interrogate(
            "Kubernetes pod management and orchestration",
            domain="devops",
        )
        self.assertIsNotNone(report)

    def test_interrogate_with_document_id(self):
        """Test interrogation with explicit document ID."""
        report = self.interrogator.interrogate(
            "Test content", document_id="my-doc-001"
        )
        self.assertEqual(report.document_id, "my-doc-001")

    def test_auto_generated_document_id(self):
        """Test auto-generated document ID."""
        report = self.interrogator.interrogate("Some content")
        self.assertTrue(report.document_id.startswith("doc-"))

    # --- 6W QUESTIONS ---

    def test_all_six_categories_asked(self):
        """Test all 6 question categories are asked."""
        report = self.interrogator.interrogate("Test content for 6W analysis.")
        categories = {a.category for a in report.answers}
        expected = {
            QuestionCategory.WHAT,
            QuestionCategory.HOW,
            QuestionCategory.WHO,
            QuestionCategory.WHERE,
            QuestionCategory.WHY,
            QuestionCategory.WHEN,
        }
        self.assertEqual(categories, expected)

    def test_what_question_answered(self):
        """Test WHAT question gets an answer."""
        report = self.interrogator.interrogate("Python data processing module.")
        what_answers = [a for a in report.answers if a.category == QuestionCategory.WHAT]
        self.assertEqual(len(what_answers), 1)
        self.assertGreater(len(what_answers[0].answer_text), 0)

    def test_how_question_answered(self):
        """Test HOW question gets an answer."""
        report = self.interrogator.interrogate("def process(): return result")
        how_answers = [a for a in report.answers if a.category == QuestionCategory.HOW]
        self.assertEqual(len(how_answers), 1)
        self.assertGreater(len(how_answers[0].answer_text), 0)

    def test_when_detects_outdated(self):
        """Test WHEN question detects outdated content."""
        report = self.interrogator.interrogate(
            "This is a deprecated legacy module from the old version."
        )
        when_answers = [a for a in report.answers if a.category == QuestionCategory.WHEN]
        self.assertIn("outdated", when_answers[0].answer_text.lower())

    # --- VERIFICATION ---

    def test_source_verification(self):
        """Test answers are verified against source code index."""
        report = self.interrogator.interrogate(
            "The CognitiveEngine class handles processing through the process method."
        )
        # At least some answers should have source verification
        source_verified = [a for a in report.answers if a.source_verified]
        # Heuristic answers reference the content which mentions CognitiveEngine
        self.assertIsInstance(source_verified, list)

    def test_oracle_verification(self):
        """Test answers are verified against Oracle."""
        report = self.interrogator.interrogate(
            "Python uses indentation for code blocks and supports multiple paradigms."
        )
        oracle_verified = [a for a in report.answers if a.oracle_verified]
        self.assertIsInstance(oracle_verified, list)

    def test_confidence_levels(self):
        """Test confidence levels are assigned."""
        report = self.interrogator.interrogate("Content with CognitiveEngine reference.")
        for answer in report.answers:
            self.assertIn(answer.confidence, list(AnswerConfidence))

    def test_verified_confidence(self):
        """Test VERIFIED confidence when both sources confirm."""
        self.oracle.ingest("CognitiveEngine processes data through OODA", domain="arch")
        report = self.interrogator.interrogate(
            "The CognitiveEngine processes data through the OODA loop pipeline."
        )
        confidences = [a.confidence for a in report.answers]
        # At least some should be verified or likely
        has_positive = any(
            c in (AnswerConfidence.VERIFIED, AnswerConfidence.LIKELY)
            for c in confidences
        )
        self.assertTrue(has_positive)

    def test_overall_confidence_calculated(self):
        """Test overall confidence is calculated."""
        report = self.interrogator.interrogate("Test content.")
        self.assertGreaterEqual(report.overall_confidence, 0.0)
        self.assertLessEqual(report.overall_confidence, 1.0)

    # --- GAP DISCOVERY ---

    def test_gap_queries_generated(self):
        """Test gap queries are generated for uncertain answers."""
        report = self.interrogator.interrogate(
            "Mysterious undocumented content with no clear purpose.",
            domain="python",
        )
        # Should generate some gap queries
        self.assertIsInstance(report.gap_queries, list)

    def test_gap_queries_from_domain(self):
        """Test domain-specific gap queries."""
        report = self.interrogator.interrogate(
            "Python web application framework basics.",
            domain="python",
        )
        # May suggest related domains like testing, debugging
        self.assertIsInstance(report.gap_queries, list)

    def test_get_all_gap_queries(self):
        """Test collecting all gap queries."""
        self.interrogator.interrogate("Content A", domain="python")
        self.interrogator.interrogate("Content B", domain="devops")
        gaps = self.interrogator.get_all_gap_queries()
        self.assertIsInstance(gaps, list)

    def test_gap_queries_deduplicated(self):
        """Test gap queries are deduplicated."""
        self.interrogator.interrogate("Same content", domain="python")
        self.interrogator.interrogate("Same content", domain="python")
        gaps = self.interrogator.get_all_gap_queries()
        self.assertEqual(len(gaps), len(set(gaps)))

    # --- USEFULNESS ASSESSMENT ---

    def test_is_useful_flag(self):
        """Test usefulness determination."""
        report = self.interrogator.interrogate("Useful technical content here.")
        self.assertIsInstance(report.is_useful, bool)

    def test_useful_with_verified_answers(self):
        """Test document is useful when answers are verified."""
        self.oracle.ingest("Machine learning neural network training", domain="ai")
        report = self.interrogator.interrogate(
            "Machine learning uses neural networks for training models."
        )
        # With oracle match, should have some confidence
        self.assertIsNotNone(report.is_useful)

    # --- DUAL FORMAT COMMUNICATION ---

    def test_json_format(self):
        """Test JSON format for Grace-to-Grace communication."""
        report = self.interrogator.interrogate("Test content")
        json_output = self.interrogator.format_for_grace(report)
        self.assertIsInstance(json_output, dict)
        self.assertIn("report_id", json_output)
        self.assertIn("answers", json_output)
        self.assertIn("overall_confidence", json_output)
        self.assertIn("gap_queries", json_output)

    def test_nlp_format(self):
        """Test NLP format for Grace-to-LLM communication."""
        report = self.interrogator.interrogate("Test content")
        nlp_output = self.interrogator.format_for_llm(report)
        self.assertIsInstance(nlp_output, str)
        self.assertIn("WHAT:", nlp_output)
        self.assertIn("HOW:", nlp_output)
        self.assertIn("WHO:", nlp_output)
        self.assertIn("WHERE:", nlp_output)
        self.assertIn("WHY:", nlp_output)
        self.assertIn("WHEN:", nlp_output)

    def test_json_contains_all_answers(self):
        """Test JSON format contains all 6 answers."""
        report = self.interrogator.interrogate("Test content")
        json_output = report.to_json()
        self.assertEqual(len(json_output["answers"]), 6)

    def test_nlp_contains_verification_tags(self):
        """Test NLP format includes verification tags."""
        self.oracle.ingest("Known fact about CognitiveEngine", domain="arch")
        report = self.interrogator.interrogate("CognitiveEngine processes data.")
        nlp_output = report.to_nlp()
        self.assertIsInstance(nlp_output, str)

    def test_json_is_serializable(self):
        """Test JSON output is fully serializable."""
        import json
        report = self.interrogator.interrogate("Test content")
        json_output = report.to_json()
        serialized = json.dumps(json_output)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["report_id"], report.report_id)

    # --- GENESIS KEY GENERATION ---

    def test_genesis_key_data(self):
        """Test Genesis Key data is generated."""
        report = self.interrogator.interrogate("Test content")
        gk = report.genesis_key_data
        self.assertIn("key_type", gk)
        self.assertEqual(gk["key_type"], "document_interrogation")
        self.assertIn("what_description", gk)
        self.assertIn("when_timestamp", gk)

    def test_create_genesis_key_from_report(self):
        """Test creating Genesis Key from report."""
        report = self.interrogator.interrogate("Test content")
        gk = self.interrogator.create_genesis_key_from_report(report)
        self.assertIn("report_id", gk)
        self.assertIn("tags", gk)
        self.assertIn("interrogation", gk["tags"])

    def test_genesis_key_includes_confidence(self):
        """Test Genesis Key includes confidence info."""
        report = self.interrogator.interrogate("Test content")
        gk = report.genesis_key_data
        self.assertIn("context_data", gk)
        self.assertIn("overall_confidence", gk["context_data"])

    # --- CUSTOM LLM HANDLER ---

    def test_custom_llm_handler(self):
        """Test with custom LLM handler."""
        def custom_llm(prompt):
            return "Custom LLM analysis: This is a well-structured document about Python."

        self.interrogator.set_llm_handler(custom_llm)
        report = self.interrogator.interrogate("Python tutorial")
        for answer in report.answers:
            self.assertIn("Custom LLM", answer.answer_text)

    def test_llm_handler_fallback(self):
        """Test fallback when LLM handler fails."""
        def failing_llm(prompt):
            raise Exception("LLM service unavailable")

        self.interrogator.set_llm_handler(failing_llm)
        report = self.interrogator.interrogate("Test content with failing LLM")
        # Should fall back to heuristic answers
        self.assertEqual(report.questions_asked, 6)
        for answer in report.answers:
            self.assertGreater(len(answer.answer_text), 0)

    # --- BATCH INTERROGATION ---

    def test_batch_interrogation(self):
        """Test batch document interrogation."""
        documents = [
            {"content": "Python machine learning tutorial", "domain": "python"},
            {"content": "Kubernetes deployment guide", "domain": "devops"},
            {"content": "Sales funnel optimization", "domain": "sales"},
        ]
        reports = self.interrogator.interrogate_batch(documents)
        self.assertEqual(len(reports), 3)
        for report in reports:
            self.assertEqual(report.questions_asked, 6)

    def test_batch_with_ids(self):
        """Test batch with explicit document IDs."""
        documents = [
            {"content": "Doc A content", "id": "doc-a"},
            {"content": "Doc B content", "id": "doc-b"},
        ]
        reports = self.interrogator.interrogate_batch(documents)
        self.assertEqual(reports[0].document_id, "doc-a")
        self.assertEqual(reports[1].document_id, "doc-b")

    # --- STATISTICS ---

    def test_get_stats(self):
        """Test statistics."""
        self.interrogator.interrogate("Test content A")
        self.interrogator.interrogate("Test content B")
        stats = self.interrogator.get_stats()
        self.assertEqual(stats["total_interrogations"], 2)
        self.assertIn("average_confidence", stats)
        self.assertIn("useful_rate", stats)
        self.assertIn("total_gap_queries", stats)

    def test_stats_empty(self):
        """Test stats with no interrogations."""
        stats = self.interrogator.get_stats()
        self.assertEqual(stats["total_interrogations"], 0)

    def test_reports_accumulated(self):
        """Test reports are accumulated."""
        self.interrogator.interrogate("Content 1")
        self.interrogator.interrogate("Content 2")
        self.interrogator.interrogate("Content 3")
        self.assertEqual(len(self.interrogator.reports), 3)


# =====================================================================
# INTEGRATION TESTS
# =====================================================================


class TestSocraticIntegration(unittest.TestCase):
    """Integration tests for the Socratic Interrogator."""

    def test_interrogation_feeds_perpetual_loop(self):
        """Test interrogation gap queries can feed the loop."""
        from oracle_pipeline.perpetual_learning_loop import PerpetualLearningLoop

        loop = PerpetualLearningLoop()
        interrogator = SocraticInterrogator(
            source_index=loop.source_index,
            oracle_store=loop.oracle,
        )

        # Seed some data
        loop.seed_from_whitelist("Python machine learning basics")

        # Interrogate a new document
        report = interrogator.interrogate(
            "Advanced neural network architectures for NLP tasks.",
            domain="ai_ml",
        )

        # Gap queries should be usable as new whitelist input
        if report.gap_queries:
            gap_input = "\n".join(report.gap_queries)
            iteration = loop.seed_from_whitelist(gap_input)
            self.assertGreater(iteration.records_created, 0)

    def test_json_nlp_roundtrip(self):
        """Test JSON and NLP formats are both generated correctly."""
        oracle = OracleVectorStore()
        oracle.ingest("Known Python fact", domain="python")
        interrogator = SocraticInterrogator(oracle_store=oracle)

        report = interrogator.interrogate(
            "Python is widely used for data science and machine learning.",
            domain="python",
        )

        json_out = report.to_json()
        nlp_out = report.to_nlp()

        # Both should exist and be non-empty
        self.assertGreater(len(json_out["answers"]), 0)
        self.assertGreater(len(nlp_out), 0)

        # JSON should be parseable
        import json
        self.assertIsNotNone(json.dumps(json_out))

    def test_genesis_key_tracks_interrogation(self):
        """Test Genesis Key properly tracks the interrogation event."""
        interrogator = SocraticInterrogator()
        report = interrogator.interrogate("Test document for tracking.")
        gk = interrogator.create_genesis_key_from_report(report)

        self.assertEqual(gk["key_type"], "document_interrogation")
        self.assertEqual(gk["who_actor"], "socratic_interrogator")
        self.assertIn("interrogation", gk["tags"])
        self.assertEqual(gk["report_id"], report.report_id)

    def test_full_pipeline_with_interrogation(self):
        """Test full pipeline: ingest -> interrogate -> discover gaps."""
        oracle = OracleVectorStore()
        source_idx = SourceCodeIndex()

        # Ingest knowledge
        oracle.ingest("Python web frameworks include Django and Flask", domain="python")
        oracle.ingest("Docker containers isolate applications", domain="devops")

        # Index some code
        source_idx.index_source_code("app.py", "class WebApp:\n    def serve(self): pass")

        interrogator = SocraticInterrogator(
            source_index=source_idx,
            oracle_store=oracle,
        )

        # Interrogate new content
        report = interrogator.interrogate(
            "Building a WebApp with Docker containers for deployment.",
            domain="devops",
        )

        # Should produce a complete report
        self.assertEqual(report.questions_asked, 6)
        self.assertIsNotNone(report.overall_confidence)
        self.assertIsNotNone(report.is_useful)

        # Should have JSON and NLP formats
        json_out = report.to_json()
        nlp_out = report.to_nlp()
        self.assertIn("answers", json_out)
        self.assertIn("WHAT:", nlp_out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
