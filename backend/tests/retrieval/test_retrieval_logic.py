"""
Tests for backend.retrieval modules — real logic with mocked externals.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import asdict


# ═══════════════════════════════════════════════════════════════════════════
# 1. DocumentRetriever.build_context  (pure logic, no mocks needed)
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildContext:
    """Tests for DocumentRetriever.build_context — pure string formatting."""

    def _make_retriever(self):
        """Create a retriever with mocked externals."""
        emb = MagicMock()
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import DocumentRetriever
            return DocumentRetriever(embedding_model=emb)

    def test_empty_chunks_returns_empty(self):
        r = self._make_retriever()
        assert r.build_context([]) == ""

    def test_single_chunk_with_source(self):
        r = self._make_retriever()
        chunks = [{"text": "Hello world", "score": 0.85,
                    "metadata": {"filename": "test.md"}}]
        ctx = r.build_context(chunks, include_sources=True)
        assert "[Document 1: test.md (relevance: 85.00%)]" in ctx
        assert "Hello world" in ctx

    def test_single_chunk_without_source(self):
        r = self._make_retriever()
        chunks = [{"text": "abc", "metadata": {}}]
        ctx = r.build_context(chunks, include_sources=False)
        assert ctx.startswith("[Document 1]")
        assert "abc" in ctx

    def test_max_length_truncation(self):
        r = self._make_retriever()
        # "[Document 1]\n" is ~14 chars; first chunk text is 20 chars → total ~36
        # second chunk would push over 80
        chunks = [{"text": "A" * 20}, {"text": "B" * 20}]
        ctx = r.build_context(chunks, max_length=40, include_sources=False)
        # Only first chunk fits within 40 chars
        assert "A" in ctx
        assert "B" not in ctx

    def test_multiple_chunks_order(self):
        r = self._make_retriever()
        chunks = [{"text": "first"}, {"text": "second"}, {"text": "third"}]
        ctx = r.build_context(chunks, include_sources=False)
        assert ctx.index("first") < ctx.index("second") < ctx.index("third")

    def test_skips_empty_text(self):
        r = self._make_retriever()
        chunks = [{"text": ""}, {"text": "real content"}]
        ctx = r.build_context(chunks, include_sources=False)
        assert "real content" in ctx
        # Empty chunk should be skipped, so numbering continues
        assert "[Document 2]" in ctx


# ═══════════════════════════════════════════════════════════════════════════
# 2. DocumentRetriever.__init__ validation
# ═══════════════════════════════════════════════════════════════════════════

class TestDocumentRetrieverInit:
    def test_no_embedding_model_raises(self):
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import DocumentRetriever
            with pytest.raises(ValueError, match="embedding_model is required"):
                DocumentRetriever(embedding_model=None)

    def test_custom_collection_name(self):
        emb = MagicMock()
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import DocumentRetriever
            r = DocumentRetriever(collection_name="custom_col", embedding_model=emb)
            assert r.collection_name == "custom_col"


# ═══════════════════════════════════════════════════════════════════════════
# 3. DocumentRetriever.retrieve — empty / whitespace guard
# ═══════════════════════════════════════════════════════════════════════════

class TestRetrieveEmptyQuery:
    def test_empty_query_returns_empty(self):
        emb = MagicMock()
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import DocumentRetriever
            r = DocumentRetriever(embedding_model=emb)
            assert r.retrieve("") == []

    def test_whitespace_query_returns_empty(self):
        emb = MagicMock()
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import DocumentRetriever
            r = DocumentRetriever(embedding_model=emb)
            assert r.retrieve("   ") == []


# ═══════════════════════════════════════════════════════════════════════════
# 4. DocumentReranker.rerank — model-less path
# ═══════════════════════════════════════════════════════════════════════════

class TestDocumentRerankerNoModel:
    """When torch/sentence_transformers unavailable, reranker returns chunks unchanged."""

    def _make_reranker_disabled(self):
        with patch("backend.retrieval.reranker._get_torch", return_value=None), \
             patch("backend.retrieval.reranker._get_cross_encoder", return_value=None):
            from backend.retrieval.reranker import DocumentReranker
            return DocumentReranker()

    def test_rerank_returns_original_when_no_model(self):
        rr = self._make_reranker_disabled()
        chunks = [{"text": "a", "score": 0.9}, {"text": "b", "score": 0.5}]
        result = rr.rerank("query", chunks)
        assert result == chunks

    def test_rerank_empty_chunks(self):
        rr = self._make_reranker_disabled()
        assert rr.rerank("q", []) == []

    def test_rerank_with_model_scoring(self):
        """Simulate a working model that returns numpy-like scores."""
        import numpy as np
        mock_torch = MagicMock()
        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.1, 0.9, 0.5])

        with patch("backend.retrieval.reranker._get_torch", return_value=mock_torch), \
             patch("backend.retrieval.reranker._get_cross_encoder", return_value=MagicMock()):
            from backend.retrieval.reranker import DocumentReranker
            rr = DocumentReranker.__new__(DocumentReranker)
            rr.model = mock_model
            rr.device = "cpu"
            rr.use_half_precision = False
            rr.model_name = "test"

        chunks = [
            {"text": "low", "score": 0.8},
            {"text": "high", "score": 0.3},
            {"text": "mid", "score": 0.5},
        ]
        result = rr.rerank("test query", chunks)
        # Sorted by rerank_score descending: high(0.9), mid(0.5), low(0.1)
        assert result[0]["text"] == "high"
        assert result[0]["rerank_score"] == pytest.approx(0.9)
        assert result[-1]["text"] == "low"

    def test_rerank_top_k(self):
        """top_k limits output size."""
        import numpy as np
        mock_torch = MagicMock()
        mock_torch.no_grad.return_value.__enter__ = MagicMock()
        mock_torch.no_grad.return_value.__exit__ = MagicMock()

        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.9, 0.8, 0.7])

        from backend.retrieval.reranker import DocumentReranker
        rr = DocumentReranker.__new__(DocumentReranker)
        rr.model = mock_model
        rr.device = "cpu"
        rr.use_half_precision = False
        rr.model_name = "test"

        with patch("backend.retrieval.reranker._get_torch", return_value=mock_torch):
            chunks = [{"text": f"c{i}"} for i in range(3)]
            result = rr.rerank("q", chunks, top_k=2)
            assert len(result) == 2


# ═══════════════════════════════════════════════════════════════════════════
# 5. query_intelligence — dataclasses & pure helpers
# ═══════════════════════════════════════════════════════════════════════════

class TestConfidenceMetrics:
    def test_high_quality_above_threshold(self):
        from backend.retrieval.query_intelligence import ConfidenceMetrics
        m = ConfidenceMetrics(overall_score=0.8)
        assert m.is_high_quality(0.7) is True

    def test_high_quality_below_threshold(self):
        from backend.retrieval.query_intelligence import ConfidenceMetrics
        m = ConfidenceMetrics(overall_score=0.5)
        assert m.is_high_quality(0.7) is False

    def test_exact_threshold_is_high_quality(self):
        from backend.retrieval.query_intelligence import ConfidenceMetrics
        m = ConfidenceMetrics(overall_score=0.7)
        assert m.is_high_quality(0.7) is True


class TestKnowledgeGap:
    def test_to_dict(self):
        from backend.retrieval.query_intelligence import KnowledgeGap
        g = KnowledgeGap(
            gap_id="g1", topic="deploy", specific_question="Where?",
            required=True, suggestions=["AWS", "GCP"]
        )
        d = g.to_dict()
        assert d["gap_id"] == "g1"
        assert d["suggestions"] == ["AWS", "GCP"]
        assert d["required"] is True

    def test_default_suggestions_empty(self):
        from backend.retrieval.query_intelligence import KnowledgeGap
        g = KnowledgeGap(gap_id="x", topic="t", specific_question="q")
        assert g.suggestions == []


class TestQueryResult:
    def test_to_dict_structure(self):
        from backend.retrieval.query_intelligence import (
            QueryResult, QueryTier, ConfidenceMetrics, KnowledgeGap
        )
        qr = QueryResult(
            tier=QueryTier.MODEL_KNOWLEDGE,
            success=True,
            response="answer",
            confidence=ConfidenceMetrics(overall_score=0.85),
            warnings=["warn1"],
        )
        d = qr.to_dict()
        assert d["tier"] == "MODEL_KNOWLEDGE"
        assert d["success"] is True
        assert d["confidence"] == 0.85
        assert d["knowledge_gaps"] == []

    def test_to_dict_with_gaps(self):
        from backend.retrieval.query_intelligence import (
            QueryResult, QueryTier, ConfidenceMetrics, KnowledgeGap
        )
        gap = KnowledgeGap(gap_id="g1", topic="t", specific_question="q?")
        qr = QueryResult(
            tier=QueryTier.USER_CONTEXT,
            success=False,
            response="need info",
            confidence=ConfidenceMetrics(),
            knowledge_gaps=[gap],
        )
        d = qr.to_dict()
        assert len(d["knowledge_gaps"]) == 1
        assert d["knowledge_gaps"][0]["gap_id"] == "g1"


# ═══════════════════════════════════════════════════════════════════════════
# 6. MultiTierQueryHandler — _assess_vectordb_quality (pure computation)
# ═══════════════════════════════════════════════════════════════════════════

class TestAssessVectordbQuality:
    def _make_handler(self):
        from backend.retrieval.query_intelligence import MultiTierQueryHandler
        return MultiTierQueryHandler(
            retriever=MagicMock(), llm_client=MagicMock()
        )

    def test_empty_chunks_zero_score(self):
        h = self._make_handler()
        m = h._assess_vectordb_quality([], "test query")
        assert m.overall_score == 0.0
        assert m.result_count == 0

    def test_good_chunks_high_score(self):
        h = self._make_handler()
        chunks = [{"score": 0.9}, {"score": 0.85}, {"score": 0.8},
                  {"score": 0.75}, {"score": 0.7}]
        m = h._assess_vectordb_quality(chunks, "test")
        assert m.overall_score > 0.6
        assert m.result_count == 5
        assert m.avg_similarity == pytest.approx(0.8)


class TestAssessModelConfidence:
    def _make_handler(self):
        from backend.retrieval.query_intelligence import MultiTierQueryHandler
        return MultiTierQueryHandler(
            retriever=MagicMock(), llm_client=MagicMock()
        )

    def test_uncertain_response(self):
        h = self._make_handler()
        m = h._assess_model_confidence("I'm not sure about that.", "q")
        assert m.uncertainty_detected is True
        assert m.overall_score == pytest.approx(0.2)

    def test_confident_long_response(self):
        h = self._make_handler()
        resp = "This is a detailed and comprehensive answer " * 5
        m = h._assess_model_confidence(resp, "q")
        assert m.uncertainty_detected is False
        assert m.overall_score == 1.0

    def test_very_short_response_low_confidence(self):
        h = self._make_handler()
        m = h._assess_model_confidence("Yes.", "q")
        assert m.overall_score == pytest.approx(0.3)


# ═══════════════════════════════════════════════════════════════════════════
# 7. MultiTierQueryHandler — _should_use_internet_search
# ═══════════════════════════════════════════════════════════════════════════

class TestShouldUseInternetSearch:
    def _make_handler(self):
        from backend.retrieval.query_intelligence import MultiTierQueryHandler
        return MultiTierQueryHandler(
            retriever=MagicMock(), llm_client=MagicMock()
        )

    def test_current_info_triggers_search(self):
        h = self._make_handler()
        assert h._should_use_internet_search("What is the latest Python release?", None) is True

    def test_personal_query_no_search(self):
        h = self._make_handler()
        assert h._should_use_internet_search("How do I configure my project?", None) is False

    def test_model_doesnt_know_triggers_search(self):
        from backend.retrieval.query_intelligence import QueryResult, QueryTier, ConfidenceMetrics
        h = self._make_handler()
        tier2 = QueryResult(
            tier=QueryTier.MODEL_KNOWLEDGE, success=True,
            response="I don't have information about that topic.",
            confidence=ConfidenceMetrics(overall_score=0.2),
        )
        assert h._should_use_internet_search("Who won the award?", tier2) is True

    def test_factual_lookup_triggers_search(self):
        h = self._make_handler()
        assert h._should_use_internet_search("What is the Stripe API documentation URL?", None) is True


# ═══════════════════════════════════════════════════════════════════════════
# 8. MultiTierQueryHandler — _identify_knowledge_gaps
# ═══════════════════════════════════════════════════════════════════════════

class TestIdentifyKnowledgeGaps:
    def _make_handler(self):
        from backend.retrieval.query_intelligence import MultiTierQueryHandler
        return MultiTierQueryHandler(
            retriever=MagicMock(), llm_client=MagicMock()
        )

    def test_deploy_query_gets_environment_gap(self):
        from backend.retrieval.query_intelligence import QueryResult, QueryTier, ConfidenceMetrics
        h = self._make_handler()
        tier1 = QueryResult(tier=QueryTier.VECTORDB, success=False,
                            response="", confidence=ConfidenceMetrics())
        gaps = h._identify_knowledge_gaps("How to deploy the app?", tier1)
        topics = [g.topic for g in gaps]
        assert "deployment_environment" in topics

    def test_config_query_gets_config_gap(self):
        from backend.retrieval.query_intelligence import QueryResult, QueryTier, ConfidenceMetrics
        h = self._make_handler()
        tier1 = QueryResult(tier=QueryTier.VECTORDB, success=False,
                            response="", confidence=ConfidenceMetrics())
        gaps = h._identify_knowledge_gaps("How to configure the database?", tier1)
        topics = [g.topic for g in gaps]
        assert "configuration_details" in topics

    def test_generic_query_gets_general_gap(self):
        from backend.retrieval.query_intelligence import QueryResult, QueryTier, ConfidenceMetrics
        h = self._make_handler()
        tier1 = QueryResult(tier=QueryTier.VECTORDB, success=False,
                            response="", confidence=ConfidenceMetrics())
        gaps = h._identify_knowledge_gaps("Tell me about the system", tier1)
        assert any(g.topic == "general_context" for g in gaps)


# ═══════════════════════════════════════════════════════════════════════════
# 9. CognitiveRetriever._analyze_query  (pure logic)
# ═══════════════════════════════════════════════════════════════════════════

class TestAnalyzeQuery:
    def _make_cog_retriever(self):
        """Build CognitiveRetriever with all externals stubbed."""
        with patch("backend.retrieval.cognitive_retriever.CognitiveEngine"), \
             patch("backend.retrieval.cognitive_retriever.get_session", return_value=iter([MagicMock()])), \
             patch("backend.retrieval.cognitive_retriever.LearningMemoryManager"), \
             patch("backend.retrieval.cognitive_retriever.TrustScorer"), \
             patch("backend.retrieval.cognitive_retriever.KNOWLEDGE_BASE_PATH", "."):
            from backend.retrieval.cognitive_retriever import CognitiveRetriever
            return CognitiveRetriever(
                retriever=MagicMock(),
                enable_cognitive=False,
                enable_learning=False,
            )

    def test_question_detected(self):
        cr = self._make_cog_retriever()
        result = cr._analyze_query("What is the meaning of life?")
        assert result["type"] == "question"
        assert result["is_question"] is True

    def test_keyword_query_short(self):
        cr = self._make_cog_retriever()
        result = cr._analyze_query("Python API")
        assert result["type"] == "keyword"
        assert result["word_count"] == 2

    def test_descriptive_query(self):
        cr = self._make_cog_retriever()
        result = cr._analyze_query("I need information about the deployment pipeline for production")
        assert result["type"] == "descriptive"

    def test_high_ambiguity(self):
        cr = self._make_cog_retriever()
        result = cr._analyze_query("some thing about stuff like any topic")
        assert result["ambiguity"] == "high"

    def test_low_ambiguity(self):
        cr = self._make_cog_retriever()
        result = cr._analyze_query("Python FastAPI deployment Kubernetes")
        assert result["ambiguity"] == "low"

    def test_has_keywords_uppercase(self):
        cr = self._make_cog_retriever()
        result = cr._analyze_query("Tell me about AWS Lambda")
        assert result["has_keywords"] is True


# ═══════════════════════════════════════════════════════════════════════════
# 10. CognitiveRetriever._assess_retrieval_quality (pure computation)
# ═══════════════════════════════════════════════════════════════════════════

class TestAssessRetrievalQuality:
    def _make_cog_retriever(self):
        with patch("backend.retrieval.cognitive_retriever.CognitiveEngine"), \
             patch("backend.retrieval.cognitive_retriever.get_session", return_value=iter([MagicMock()])), \
             patch("backend.retrieval.cognitive_retriever.LearningMemoryManager"), \
             patch("backend.retrieval.cognitive_retriever.TrustScorer"), \
             patch("backend.retrieval.cognitive_retriever.KNOWLEDGE_BASE_PATH", "."):
            from backend.retrieval.cognitive_retriever import CognitiveRetriever
            return CognitiveRetriever(
                retriever=MagicMock(),
                enable_cognitive=False,
                enable_learning=False,
            )

    def test_empty_chunks_zero(self):
        cr = self._make_cog_retriever()
        q = cr._assess_retrieval_quality("q", [], {"type": "question"})
        assert q == 0.0

    def test_good_chunks_high_quality(self):
        cr = self._make_cog_retriever()
        chunks = [
            {"score": 0.9, "confidence_score": 0.9},
            {"score": 0.85, "confidence_score": 0.85},
            {"score": 0.8, "confidence_score": 0.8},
            {"score": 0.75, "confidence_score": 0.75},
            {"score": 0.7, "confidence_score": 0.7},
        ]
        q = cr._assess_retrieval_quality("test", chunks, {"type": "question"})
        assert q > 0.6

    def test_single_chunk_partial_coverage(self):
        cr = self._make_cog_retriever()
        chunks = [{"score": 0.95, "confidence_score": 0.95}]
        q = cr._assess_retrieval_quality("test", chunks, {"type": "keyword"})
        # coverage_score = 1/5 = 0.2, so quality is lower
        assert 0.0 < q < 0.9


# ═══════════════════════════════════════════════════════════════════════════
# 11. deterministic_rag_validator — RAGIssue / RAGValidationReport
# ═══════════════════════════════════════════════════════════════════════════

class TestRAGValidatorDataclasses:
    def test_rag_issue_fields(self):
        from backend.retrieval.deterministic_rag_validator import RAGIssue
        issue = RAGIssue(
            check="test_check", severity="critical",
            message="something broke", fix_suggestion="fix it"
        )
        assert issue.severity == "critical"
        d = asdict(issue)
        assert d["fix_suggestion"] == "fix it"

    def test_report_to_dict(self):
        from backend.retrieval.deterministic_rag_validator import (
            RAGValidationReport, RAGIssue
        )
        report = RAGValidationReport(
            timestamp="2026-03-14T00:00:00Z",
            total_issues=2, critical_count=1,
            warning_count=1, info_count=0,
            checks_run=["a", "b"],
            issues=[
                RAGIssue(check="a", severity="critical", message="bad"),
                RAGIssue(check="b", severity="warning", message="meh"),
            ],
            stats={"total_documents": 5},
        )
        d = report.to_dict()
        assert d["total_issues"] == 2
        assert d["stats"]["total_documents"] == 5
        assert len(d["issues"]) == 2

    def test_report_counts(self):
        from backend.retrieval.deterministic_rag_validator import RAGValidationReport
        r = RAGValidationReport(
            timestamp="t", total_issues=3,
            critical_count=1, warning_count=1, info_count=1,
            checks_run=[], issues=[], stats={},
        )
        assert r.critical_count + r.warning_count + r.info_count == r.total_issues


# ═══════════════════════════════════════════════════════════════════════════
# 12. deterministic_rag_validator — check_embedding_model (file-based)
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckEmbeddingModel:
    def test_missing_embedder_file(self, tmp_path):
        with patch("backend.retrieval.deterministic_rag_validator.BACKEND_ROOT", tmp_path):
            from backend.retrieval.deterministic_rag_validator import check_embedding_model
            issues = check_embedding_model()
            assert any(i.severity == "critical" for i in issues)
            assert any("not found" in i.message for i in issues)

    def test_valid_embedder_file(self, tmp_path):
        emb_dir = tmp_path / "embedding"
        emb_dir.mkdir()
        (emb_dir / "embedder.py").write_text(
            "class EmbeddingModel:\n"
            "    def embed_text(self, texts): pass\n"
            "def get_embedding_model(): pass\n"
        )
        (tmp_path / "settings.py").write_text("EMBEDDING_MODEL = 'test'\n")
        with patch("backend.retrieval.deterministic_rag_validator.BACKEND_ROOT", tmp_path):
            from backend.retrieval.deterministic_rag_validator import check_embedding_model
            issues = check_embedding_model()
            assert not any(i.severity == "critical" for i in issues)


# ═══════════════════════════════════════════════════════════════════════════
# 13. deterministic_rag_validator — check_rag_import_chain
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckRagImportChain:
    def test_missing_files_reported(self, tmp_path):
        with patch("backend.retrieval.deterministic_rag_validator.BACKEND_ROOT", tmp_path):
            from backend.retrieval.deterministic_rag_validator import check_rag_import_chain
            issues = check_rag_import_chain()
            assert len(issues) > 0
            assert all(i.severity == "warning" for i in issues)

    def test_syntax_error_detected(self, tmp_path):
        ret_dir = tmp_path / "retrieval"
        ret_dir.mkdir()
        (ret_dir / "retriever.py").write_text("def broken(:\n")
        with patch("backend.retrieval.deterministic_rag_validator.BACKEND_ROOT", tmp_path):
            from backend.retrieval.deterministic_rag_validator import check_rag_import_chain
            issues = check_rag_import_chain()
            assert any(i.severity == "critical" and "Syntax error" in i.message for i in issues)


# ═══════════════════════════════════════════════════════════════════════════
# 14. _generate_context_request_message
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateContextRequestMessage:
    def _make_handler(self):
        from backend.retrieval.query_intelligence import MultiTierQueryHandler
        return MultiTierQueryHandler(retriever=MagicMock(), llm_client=MagicMock())

    def test_message_contains_questions(self):
        from backend.retrieval.query_intelligence import KnowledgeGap
        h = self._make_handler()
        gaps = [
            KnowledgeGap(gap_id="g1", topic="env", specific_question="Which OS?",
                         suggestions=["Linux", "Windows"]),
        ]
        msg = h._generate_context_request_message("deploy", gaps)
        assert "Which OS?" in msg
        assert "Linux" in msg

    def test_message_numbers_gaps(self):
        from backend.retrieval.query_intelligence import KnowledgeGap
        h = self._make_handler()
        gaps = [
            KnowledgeGap(gap_id="a", topic="t1", specific_question="Q1?"),
            KnowledgeGap(gap_id="b", topic="t2", specific_question="Q2?"),
        ]
        msg = h._generate_context_request_message("q", gaps)
        assert "1. Q1?" in msg
        assert "2. Q2?" in msg


# ═══════════════════════════════════════════════════════════════════════════
# 15. get_retriever factory
# ═══════════════════════════════════════════════════════════════════════════

class TestGetRetriever:
    def test_returns_document_retriever(self):
        emb = MagicMock()
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import get_retriever
            r = get_retriever(collection_name="test_col", embedding_model=emb)
            assert r.collection_name == "test_col"

    def test_raises_without_model(self):
        with patch("backend.retrieval.retriever.get_qdrant_client"):
            from backend.retrieval.retriever import get_retriever
            with pytest.raises(ValueError):
                get_retriever(embedding_model=None)
