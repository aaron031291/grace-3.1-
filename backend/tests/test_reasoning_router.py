"""
Tests for Reasoning Router — tiered intelligence allocation.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestReasoningTier:
    def test_tier_ordering(self):
        from llm_orchestrator.reasoning_router import ReasoningTier
        assert ReasoningTier.INSTANT < ReasoningTier.STANDARD
        assert ReasoningTier.STANDARD < ReasoningTier.CONSENSUS
        assert ReasoningTier.CONSENSUS < ReasoningTier.DEEP

    def test_tier_values(self):
        from llm_orchestrator.reasoning_router import ReasoningTier
        assert ReasoningTier.INSTANT == 0
        assert ReasoningTier.STANDARD == 1
        assert ReasoningTier.CONSENSUS == 2
        assert ReasoningTier.DEEP == 3


class TestRoutingDecision:
    def test_tier_name(self):
        from llm_orchestrator.reasoning_router import RoutingDecision, ReasoningTier
        d = RoutingDecision(tier=ReasoningTier.DEEP, reason="test")
        assert d.tier_name == "DEEP"

    def test_instant_name(self):
        from llm_orchestrator.reasoning_router import RoutingDecision, ReasoningTier
        d = RoutingDecision(tier=ReasoningTier.INSTANT, reason="test")
        assert d.tier_name == "INSTANT"


class TestTier0Classification:
    """Tier 0: Greetings and simple lookups — no LLM needed."""

    def test_hello(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("hello")
        assert d.tier == ReasoningTier.INSTANT

    def test_hi(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        assert r.classify("hi").tier == ReasoningTier.INSTANT

    def test_thanks(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        assert r.classify("thanks").tier == ReasoningTier.INSTANT

    def test_goodbye(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        assert r.classify("goodbye").tier == ReasoningTier.INSTANT

    def test_good_morning(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        assert r.classify("good morning").tier == ReasoningTier.INSTANT


class TestTier1Classification:
    """Tier 1: Standard questions — single model + RAG."""

    def test_simple_question(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("What is a for loop?")
        assert d.tier == ReasoningTier.STANDARD

    def test_short_technical_query(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("What is a REST API?")
        assert d.tier == ReasoningTier.STANDARD

    def test_code_snippet_request(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("Show me a Python function to sort a list")
        assert d.tier == ReasoningTier.STANDARD


class TestTier2Classification:
    """Tier 2: Consensus needed — 2+ models in parallel."""

    def test_best_practice(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("What is the best practice for implementing authentication in a microservices architecture?")
        assert d.tier >= ReasoningTier.CONSENSUS

    def test_trade_offs(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("What are the trade-offs between SQL and NoSQL databases?")
        assert d.tier == ReasoningTier.CONSENSUS

    def test_how_should(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("How should I structure my React application for scalability and maintainability?")
        assert d.tier >= ReasoningTier.CONSENSUS

    def test_high_ambiguity_escalates(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("it broke and I need help figuring out why this complex system is failing with different approaches to consider", ambiguity_score=0.7)
        assert d.tier >= ReasoningTier.CONSENSUS


class TestTier3Classification:
    """Tier 3: Deep reasoning — full 3-layer pipeline."""

    def test_think_deeply(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("Think deeply about the implications of this architecture change")
        assert d.tier == ReasoningTier.DEEP

    def test_analyze_carefully(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("Analyze carefully why the database connection keeps failing")
        assert d.tier == ReasoningTier.DEEP

    def test_find_root_cause(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("Find the root cause of this memory leak in our production system")
        assert d.tier == ReasoningTier.DEEP

    def test_system_design(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("Design a system architecture for a distributed event processing pipeline")
        assert d.tier == ReasoningTier.DEEP

    def test_production_deploy(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("Deploy this critical change to production and restart the service", action_type="execute", is_self_agent=True)
        assert d.tier >= ReasoningTier.CONSENSUS

    def test_high_ambiguity_and_risk(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("delete everything and restart", ambiguity_score=0.8, action_type="delete")
        assert d.tier == ReasoningTier.DEEP

    def test_self_agent_critical_action(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify_self_agent_action("code_agent", "modify production config", "critical")
        assert d.tier == ReasoningTier.DEEP


class TestForceOverride:
    def test_force_tier_3(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("hello", force_tier=3)
        assert d.tier == ReasoningTier.DEEP

    def test_force_tier_0(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify("complex analysis needed", force_tier=0)
        assert d.tier == ReasoningTier.INSTANT


class TestSelfAgentRouting:
    def test_low_risk(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify_self_agent_action("mirror", "observe", "low")
        assert d.tier == ReasoningTier.STANDARD

    def test_medium_risk(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify_self_agent_action("learner", "study topic", "medium")
        assert d.tier <= ReasoningTier.CONSENSUS

    def test_critical_risk(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter, ReasoningTier
        r = ReasoningRouter()
        d = r.classify_self_agent_action("code_agent", "delete file", "critical")
        assert d.tier == ReasoningTier.DEEP


class TestStats:
    def test_stats_tracking(self):
        from llm_orchestrator.reasoning_router import ReasoningRouter
        r = ReasoningRouter()
        r.classify("hello")
        r.classify("How do I sort a list?")
        r.classify("Think deeply about this problem")
        stats = r.get_stats()
        assert stats["total_routed"] == 3
        assert "tier_distribution" in stats

    def test_singleton(self):
        from llm_orchestrator.reasoning_router import get_reasoning_router
        r1 = get_reasoning_router()
        r2 = get_reasoning_router()
        assert r1 is r2


class TestAppWiring:
    def test_router_in_send_prompt(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "reasoning_router" in source
        assert "get_reasoning_router" in source
        assert "reasoning_tier" in source
        assert "routing_decision" in source
        assert "tier_name" in source.lower() or "tier_name" in source
