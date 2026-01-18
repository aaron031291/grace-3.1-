"""
Enhanced Proactive Learning System

Maximum capability proactive learning with:
1. Evidence-based expansion (not just embedding gaps)
2. Multi-hop query chains
3. LLM Planner → Analyst → Critic orchestration
4. Priority queue: impact × uncertainty × freshness
5. Feedback-driven learning
6. Cross-source knowledge synthesis
7. Pattern evolution detection
8. Counterfactual generation for wrong predictions
"""

import logging
import asyncio
import json
import threading
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import uuid
import hashlib

logger = logging.getLogger(__name__)


class LearningMode(str, Enum):
    """Learning modes for different situations."""
    EVIDENCE_GAP = "evidence_gap"       # Missing evidence for claims
    UNCERTAINTY = "uncertainty"         # High uncertainty items
    STALENESS = "staleness"            # Outdated knowledge
    PATTERN_DRIFT = "pattern_drift"    # Patterns changing
    FAILURE_ANALYSIS = "failure"       # Wrong predictions
    CROSS_POLLINATE = "cross"          # Connect different topics
    FRONTIER_EXPLORE = "frontier"      # Expand knowledge boundaries


@dataclass
class LearningTarget:
    """A target for proactive learning."""
    target_id: str
    mode: LearningMode
    memory_id: Optional[str] = None
    query: str = ""
    sources: List[str] = field(default_factory=list)
    priority: float = 0.0
    uncertainty: float = 0.0
    impact: float = 0.0
    staleness: float = 0.0
    evidence_needed: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.target_id,
            "mode": self.mode.value,
            "query": self.query,
            "sources": self.sources,
            "priority": self.priority,
            "evidence_needed": self.evidence_needed
        }


@dataclass
class LLMPlan:
    """A plan from LLM orchestration."""
    plan_id: str
    objective: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    queries: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    expected_evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class LLMAnalysis:
    """Analysis from LLM analyst role."""
    analysis_id: str
    findings: List[str] = field(default_factory=list)
    evidence_links: List[str] = field(default_factory=list)
    confidence: float = 0.5
    knowledge_items: List[Dict] = field(default_factory=list)


@dataclass
class LLMCritique:
    """Critique from LLM critic role."""
    critique_id: str
    issues: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    confidence_adjustment: float = 0.0
    approved: bool = False
    suggested_queries: List[str] = field(default_factory=list)


class EnhancedProactiveLearning:
    """
    Enhanced Proactive Learning System.
    
    Uses evidence-based learning targets instead of just embedding gaps.
    Employs LLM Planner → Analyst → Critic pattern.
    """
    
    def __init__(
        self,
        oracle_hub=None,
        enhanced_memory=None,
        reverse_knn=None,
        llm_client=None,
        learning_interval_seconds: int = 300
    ):
        self._oracle_hub = oracle_hub
        self._memory = enhanced_memory
        self._reverse_knn = reverse_knn
        self._llm_client = llm_client
        
        self.learning_interval = learning_interval_seconds
        
        # Learning targets queue
        self._targets: List[LearningTarget] = []
        self._executed_queries: Set[str] = set()
        
        # Pattern evolution tracking
        self._pattern_history: Dict[str, List[Dict]] = defaultdict(list)
        
        # Failure analysis
        self._failed_predictions: List[Dict] = []
        
        # Background learning
        self._learning_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Stats
        self._stats = {
            "targets_generated": 0,
            "targets_executed": 0,
            "knowledge_added": 0,
            "evidence_found": 0,
            "patterns_updated": 0,
            "failures_analyzed": 0,
            "llm_plans": 0,
            "llm_critiques": 0,
            "last_cycle": None
        }
        
        logger.info("[ENHANCED-LEARNING] Proactive learning system initialized")
    
    # =========================================================================
    # TARGET GENERATION
    # =========================================================================
    
    async def generate_learning_targets(self) -> List[LearningTarget]:
        """Generate learning targets from all sources."""
        targets = []
        
        # 1. Evidence gaps from high-impact uncertain items
        evidence_targets = await self._find_evidence_gaps()
        targets.extend(evidence_targets)
        
        # 2. Stale knowledge that needs refresh
        stale_targets = await self._find_stale_knowledge()
        targets.extend(stale_targets)
        
        # 3. Pattern drift detection
        drift_targets = await self._detect_pattern_drift()
        targets.extend(drift_targets)
        
        # 4. Failed prediction analysis
        failure_targets = await self._analyze_failures()
        targets.extend(failure_targets)
        
        # 5. Cross-pollination opportunities
        cross_targets = await self._find_cross_pollination()
        targets.extend(cross_targets)
        
        # 6. Frontier exploration from Reverse KNN
        if self._reverse_knn:
            frontier_targets = await self._get_frontier_targets()
            targets.extend(frontier_targets)
        
        # Sort by priority
        targets.sort(key=lambda t: t.priority, reverse=True)
        
        # Deduplicate
        seen = set()
        unique_targets = []
        for target in targets:
            query_hash = hashlib.md5(target.query.lower().encode()).hexdigest()[:12]
            if query_hash not in seen and query_hash not in self._executed_queries:
                seen.add(query_hash)
                unique_targets.append(target)
        
        self._targets = unique_targets[:50]  # Keep top 50
        self._stats["targets_generated"] += len(unique_targets)
        
        return self._targets
    
    async def _find_evidence_gaps(self) -> List[LearningTarget]:
        """Find high-impact items missing evidence."""
        targets = []
        
        if not self._memory:
            return targets
        
        # Get priority items
        priority_items = self._memory.get_priority_items(limit=20)
        
        for item in priority_items:
            # Items with high impact but low confidence need evidence
            if item.impact_score > 0.6 and item.calibrated_confidence < 0.7:
                target = LearningTarget(
                    target_id=f"EV-{uuid.uuid4().hex[:8]}",
                    mode=LearningMode.EVIDENCE_GAP,
                    memory_id=item.memory_id,
                    query=f"{item.title} evidence examples proof",
                    sources=[item.source] if item.source else ["github", "stackoverflow"],
                    priority=item.priority_score * 1.5,
                    uncertainty=1.0 - item.calibrated_confidence,
                    impact=item.impact_score,
                    evidence_needed=[
                        "code examples",
                        "real-world usage",
                        "best practices",
                        "failure cases"
                    ]
                )
                targets.append(target)
        
        return targets
    
    async def _find_stale_knowledge(self) -> List[LearningTarget]:
        """Find knowledge that needs refresh."""
        targets = []
        
        if not self._memory:
            return targets
        
        expansion_targets = self._memory.get_expansion_targets()
        
        for exp in expansion_targets:
            if exp["staleness"] > 0.5:
                target = LearningTarget(
                    target_id=f"STALE-{uuid.uuid4().hex[:8]}",
                    mode=LearningMode.STALENESS,
                    memory_id=exp["memory_id"],
                    query=exp["suggested_query"] + " latest updates 2024 2025",
                    sources=["web_knowledge", "github", "documentation"],
                    priority=exp["priority"],
                    staleness=exp["staleness"],
                    impact=exp["impact"]
                )
                targets.append(target)
        
        return targets
    
    async def _detect_pattern_drift(self) -> List[LearningTarget]:
        """Detect patterns that are drifting (success rate changing)."""
        targets = []
        
        for pattern_id, history in self._pattern_history.items():
            if len(history) < 5:
                continue
            
            # Check recent vs historical success rate
            recent = history[-5:]
            historical = history[:-5]
            
            if historical:
                recent_rate = sum(h.get("success", 0) for h in recent) / len(recent)
                historical_rate = sum(h.get("success", 0) for h in historical) / len(historical)
                
                drift = abs(recent_rate - historical_rate)
                
                if drift > 0.2:  # 20% drift
                    target = LearningTarget(
                        target_id=f"DRIFT-{uuid.uuid4().hex[:8]}",
                        mode=LearningMode.PATTERN_DRIFT,
                        memory_id=pattern_id,
                        query=f"{history[-1].get('description', '')} why changed behavior",
                        sources=["stackoverflow", "github"],
                        priority=drift * 2,
                        evidence_needed=[
                            "recent changes",
                            "breaking changes",
                            "migration guides"
                        ]
                    )
                    targets.append(target)
        
        return targets
    
    async def _analyze_failures(self) -> List[LearningTarget]:
        """Analyze failed predictions to understand why."""
        targets = []
        
        for failure in self._failed_predictions[-20:]:  # Last 20 failures
            target = LearningTarget(
                target_id=f"FAIL-{uuid.uuid4().hex[:8]}",
                mode=LearningMode.FAILURE_ANALYSIS,
                memory_id=failure.get("memory_id"),
                query=f"{failure.get('title', '')} why wrong alternative approaches",
                sources=["stackoverflow", "github", "documentation"],
                priority=failure.get("impact", 0.5) * 1.5,
                evidence_needed=[
                    "alternative solutions",
                    "edge cases",
                    "common mistakes"
                ]
            )
            targets.append(target)
        
        return targets
    
    async def _find_cross_pollination(self) -> List[LearningTarget]:
        """Find opportunities to connect different knowledge areas."""
        targets = []
        
        if not self._memory:
            return targets
        
        # Get correlation stats
        corr_stats = self._memory.correlator.get_correlation_stats()
        
        # Look at top correlated clusters for cross-pollination
        for cluster in corr_stats.get("top_clusters", [])[:5]:
            if len(cluster["sources"]) >= 2:
                target = LearningTarget(
                    target_id=f"CROSS-{uuid.uuid4().hex[:8]}",
                    mode=LearningMode.CROSS_POLLINATE,
                    query=f"{cluster['claim']} integration combination best practices",
                    sources=list(cluster["sources"]),
                    priority=cluster["confidence"] * 0.8,
                    evidence_needed=[
                        "integration patterns",
                        "combined usage",
                        "synergies"
                    ]
                )
                targets.append(target)
        
        return targets
    
    async def _get_frontier_targets(self) -> List[LearningTarget]:
        """Get frontier expansion targets from Reverse KNN."""
        targets = []
        
        if not self._reverse_knn:
            return targets
        
        # Get sparse clusters
        for cluster_id, cluster in self._reverse_knn._clusters.items():
            if cluster.cluster_type.value in ["sparse", "frontier", "isolated"]:
                target = LearningTarget(
                    target_id=f"FRONT-{uuid.uuid4().hex[:8]}",
                    mode=LearningMode.FRONTIER_EXPLORE,
                    query=f"{cluster.centroid_topic} deep dive advanced techniques",
                    sources=cluster.sources,
                    priority=cluster.expansion_priority,
                    evidence_needed=[
                        "advanced examples",
                        "edge cases",
                        "expert techniques"
                    ]
                )
                targets.append(target)
        
        return targets
    
    # =========================================================================
    # LLM ORCHESTRATION: PLANNER → ANALYST → CRITIC
    # =========================================================================
    
    async def llm_plan(self, target: LearningTarget) -> LLMPlan:
        """LLM Planner: Decide what to retrieve and how."""
        plan = LLMPlan(
            plan_id=f"PLAN-{uuid.uuid4().hex[:8]}",
            objective=f"Fill knowledge gap: {target.query}"
        )
        
        prompt = f"""You are a knowledge acquisition planner.

Target Query: {target.query}
Mode: {target.mode.value}
Sources Available: {target.sources}
Evidence Needed: {target.evidence_needed}

Plan the knowledge acquisition:
1. What specific queries should we run?
2. Which sources are best for each query?
3. What evidence would increase confidence?
4. What alternative phrasings might help?

Output as JSON:
{{
    "steps": [
        {{"action": "search", "source": "...", "query": "..."}}
    ],
    "queries": ["query1", "query2"],
    "sources": ["source1"],
    "expected_evidence": ["evidence type 1"]
}}"""
        
        response = await self._call_llm(prompt)
        
        if response:
            try:
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    plan.steps = data.get("steps", [])
                    plan.queries = data.get("queries", [target.query])
                    plan.sources = data.get("sources", target.sources)
                    plan.expected_evidence = data.get("expected_evidence", [])
                    plan.confidence = 0.7
                    self._stats["llm_plans"] += 1
            except Exception as e:
                logger.debug(f"[ENHANCED-LEARNING] Plan parse error: {e}")
                plan.queries = [target.query]
                plan.sources = target.sources
        else:
            plan.queries = [target.query]
            plan.sources = target.sources
        
        return plan
    
    async def llm_analyze(
        self,
        plan: LLMPlan,
        fetched_content: List[Dict]
    ) -> LLMAnalysis:
        """LLM Analyst: Analyze fetched content and extract knowledge."""
        analysis = LLMAnalysis(
            analysis_id=f"ANALYSIS-{uuid.uuid4().hex[:8]}"
        )
        
        content_summary = "\n".join([
            f"- [{c.get('source', 'unknown')}] {c.get('title', '')}: {c.get('content', '')[:200]}"
            for c in fetched_content[:10]
        ])
        
        prompt = f"""You are a knowledge analyst extracting insights.

Objective: {plan.objective}
Expected Evidence: {plan.expected_evidence}

Fetched Content:
{content_summary}

Analyze and extract:
1. Key findings that address the objective
2. Links between findings and evidence sources
3. Confidence level in each finding
4. Structured knowledge items to store

Output as JSON:
{{
    "findings": ["finding 1", "finding 2"],
    "evidence_links": ["source 1 supports finding 1"],
    "confidence": 0.75,
    "knowledge_items": [
        {{"title": "...", "content": "...", "tags": ["..."], "confidence": 0.8}}
    ]
}}"""
        
        response = await self._call_llm(prompt)
        
        if response:
            try:
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    analysis.findings = data.get("findings", [])
                    analysis.evidence_links = data.get("evidence_links", [])
                    analysis.confidence = data.get("confidence", 0.5)
                    analysis.knowledge_items = data.get("knowledge_items", [])
            except Exception as e:
                logger.debug(f"[ENHANCED-LEARNING] Analysis parse error: {e}")
        
        return analysis
    
    async def llm_critique(
        self,
        analysis: LLMAnalysis,
        original_target: LearningTarget
    ) -> LLMCritique:
        """LLM Critic: Check for issues, missing evidence, approve/reject."""
        critique = LLMCritique(
            critique_id=f"CRIT-{uuid.uuid4().hex[:8]}"
        )
        
        prompt = f"""You are a critical reviewer checking knowledge quality.

Original Target: {original_target.query}
Evidence Needed: {original_target.evidence_needed}

Analysis Findings: {analysis.findings}
Analysis Confidence: {analysis.confidence}
Knowledge Items: {len(analysis.knowledge_items)} items

Critically evaluate:
1. Are the findings well-supported by evidence?
2. What evidence is still missing?
3. Should confidence be adjusted up or down?
4. Are there contradictions or gaps?
5. Should this be approved for storage?

Output as JSON:
{{
    "issues": ["issue 1", "issue 2"],
    "missing_evidence": ["evidence type 1"],
    "confidence_adjustment": -0.1,
    "approved": true,
    "suggested_queries": ["follow-up query if needed"]
}}"""
        
        response = await self._call_llm(prompt)
        
        if response:
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    critique.issues = data.get("issues", [])
                    critique.missing_evidence = data.get("missing_evidence", [])
                    critique.confidence_adjustment = data.get("confidence_adjustment", 0)
                    critique.approved = data.get("approved", True)
                    critique.suggested_queries = data.get("suggested_queries", [])
                    self._stats["llm_critiques"] += 1
            except Exception as e:
                logger.debug(f"[ENHANCED-LEARNING] Critique parse error: {e}")
                critique.approved = True
        else:
            critique.approved = True
        
        return critique
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM with fallback options."""
        if self._llm_client:
            try:
                return await self._llm_client.generate(prompt)
            except Exception as e:
                logger.debug(f"[ENHANCED-LEARNING] Primary LLM failed: {e}")
        
        # Try DeepSeek fallback
        try:
            from llm.deepseek_client import get_deepseek_client
            client = get_deepseek_client()
            return await client.chat(prompt)
        except Exception as e:
            logger.debug(f"[ENHANCED-LEARNING] DeepSeek fallback failed: {e}")
        
        return None
    
    # =========================================================================
    # EXECUTE LEARNING
    # =========================================================================
    
    async def execute_target(self, target: LearningTarget) -> Dict[str, Any]:
        """Execute a single learning target with full LLM orchestration."""
        result = {
            "target_id": target.target_id,
            "mode": target.mode.value,
            "success": False,
            "knowledge_added": 0,
            "evidence_found": 0
        }
        
        try:
            # Step 1: LLM Planning
            plan = await self.llm_plan(target)
            logger.info(f"[ENHANCED-LEARNING] Plan: {len(plan.queries)} queries")
            
            # Step 2: Fetch content from sources
            fetched_content = []
            for query in plan.queries[:5]:
                for source in plan.sources[:3]:
                    content = await self._fetch_from_source(source, query)
                    fetched_content.extend(content)
            
            if not fetched_content:
                result["error"] = "No content fetched"
                return result
            
            # Step 3: LLM Analysis
            analysis = await self.llm_analyze(plan, fetched_content)
            logger.info(f"[ENHANCED-LEARNING] Analysis: {len(analysis.findings)} findings")
            
            # Step 4: LLM Critique
            critique = await self.llm_critique(analysis, target)
            
            # Step 5: Store if approved
            if critique.approved and analysis.knowledge_items:
                for item_data in analysis.knowledge_items:
                    # Adjust confidence based on critique
                    adjusted_confidence = max(0.1, min(0.99,
                        item_data.get("confidence", 0.5) + critique.confidence_adjustment
                    ))
                    
                    # Ingest through Oracle Hub
                    if self._oracle_hub:
                        from oracle_intelligence.unified_oracle_hub import (
                            IntelligenceSource, IntelligenceItem
                        )
                        
                        intel_item = IntelligenceItem(
                            item_id=f"LEARN-{uuid.uuid4().hex[:8]}",
                            source=IntelligenceSource.LEARNING_MEMORY,
                            title=item_data.get("title", target.query),
                            content=item_data.get("content", ""),
                            confidence=adjusted_confidence,
                            tags=item_data.get("tags", []) + ["proactive_learning", target.mode.value]
                        )
                        
                        await self._oracle_hub.ingest(intel_item)
                        result["knowledge_added"] += 1
                
                result["evidence_found"] = len(analysis.evidence_links)
                result["success"] = True
                
                self._stats["knowledge_added"] += result["knowledge_added"]
                self._stats["evidence_found"] += result["evidence_found"]
            
            # Add follow-up queries from critique
            if critique.suggested_queries:
                for query in critique.suggested_queries[:2]:
                    follow_up = LearningTarget(
                        target_id=f"FOLLOW-{uuid.uuid4().hex[:8]}",
                        mode=target.mode,
                        query=query,
                        sources=target.sources,
                        priority=target.priority * 0.8
                    )
                    self._targets.append(follow_up)
            
            # Mark as executed
            query_hash = hashlib.md5(target.query.lower().encode()).hexdigest()[:12]
            self._executed_queries.add(query_hash)
            self._stats["targets_executed"] += 1
            
        except Exception as e:
            logger.error(f"[ENHANCED-LEARNING] Target execution failed: {e}")
            result["error"] = str(e)
        
        return result
    
    async def _fetch_from_source(
        self,
        source: str,
        query: str
    ) -> List[Dict]:
        """Fetch content from a specific source."""
        content = []
        
        try:
            from oracle_intelligence.web_knowledge import WebKnowledgeIntegration
            web_knowledge = WebKnowledgeIntegration()
            
            if source == "github":
                results = await web_knowledge.search_github_code(query, limit=3)
            elif source == "stackoverflow":
                results = await web_knowledge.search_stackoverflow(query, limit=3)
            elif source in ["web_knowledge", "documentation"]:
                results = await web_knowledge.search_documentation(query, limit=3)
            else:
                results = await web_knowledge.search_web(query, limit=3)
            
            for result in results:
                content.append({
                    "source": source,
                    "title": getattr(result, "title", query),
                    "content": getattr(result, "content", str(result))[:500],
                    "url": getattr(result, "url", None)
                })
                
        except Exception as e:
            logger.debug(f"[ENHANCED-LEARNING] Fetch from {source} failed: {e}")
        
        return content
    
    # =========================================================================
    # FAILURE RECORDING
    # =========================================================================
    
    def record_prediction_failure(
        self,
        memory_id: str,
        title: str,
        predicted_confidence: float,
        actual_outcome: str,
        impact: float = 0.5
    ):
        """Record a failed prediction for analysis."""
        self._failed_predictions.append({
            "memory_id": memory_id,
            "title": title,
            "predicted_confidence": predicted_confidence,
            "actual_outcome": actual_outcome,
            "impact": impact,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Trim
        if len(self._failed_predictions) > 100:
            self._failed_predictions = self._failed_predictions[-100:]
        
        self._stats["failures_analyzed"] += 1
    
    # =========================================================================
    # PATTERN TRACKING
    # =========================================================================
    
    def record_pattern_outcome(
        self,
        pattern_id: str,
        description: str,
        success: bool
    ):
        """Record pattern outcome for drift detection."""
        self._pattern_history[pattern_id].append({
            "description": description,
            "success": 1 if success else 0,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Trim
        if len(self._pattern_history[pattern_id]) > 100:
            self._pattern_history[pattern_id] = self._pattern_history[pattern_id][-100:]
        
        self._stats["patterns_updated"] += 1
    
    # =========================================================================
    # CONTINUOUS LEARNING LOOP
    # =========================================================================
    
    async def run_learning_cycle(self) -> Dict[str, Any]:
        """Run one complete learning cycle."""
        logger.info("[ENHANCED-LEARNING] Starting learning cycle...")
        
        results = {
            "targets_generated": 0,
            "targets_executed": 0,
            "knowledge_added": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Generate targets
        targets = await self.generate_learning_targets()
        results["targets_generated"] = len(targets)
        logger.info(f"[ENHANCED-LEARNING] Generated {len(targets)} targets")
        
        # Execute top priority targets
        for target in targets[:5]:
            exec_result = await self.execute_target(target)
            results["targets_executed"] += 1
            results["knowledge_added"] += exec_result.get("knowledge_added", 0)
        
        self._stats["last_cycle"] = datetime.utcnow().isoformat()
        
        logger.info(f"[ENHANCED-LEARNING] Cycle complete: {results['knowledge_added']} items added")
        
        return results
    
    def start_continuous_learning(self):
        """Start continuous learning in background."""
        if self._running:
            return {"status": "already_running"}
        
        self._running = True
        
        def learning_loop():
            while self._running:
                try:
                    asyncio.run(self.run_learning_cycle())
                except Exception as e:
                    logger.error(f"[ENHANCED-LEARNING] Cycle error: {e}")
                
                for _ in range(self.learning_interval):
                    if not self._running:
                        break
                    import time
                    time.sleep(1)
        
        self._learning_thread = threading.Thread(target=learning_loop, daemon=True)
        self._learning_thread.start()
        
        logger.info("[ENHANCED-LEARNING] Continuous learning started")
        return {"status": "started", "interval": self.learning_interval}
    
    def stop_continuous_learning(self):
        """Stop continuous learning."""
        self._running = False
        logger.info("[ENHANCED-LEARNING] Continuous learning stopped")
        return {"status": "stopped"}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            **self._stats,
            "pending_targets": len(self._targets),
            "executed_queries": len(self._executed_queries),
            "failed_predictions_tracked": len(self._failed_predictions),
            "patterns_tracked": len(self._pattern_history),
            "running": self._running
        }


# =============================================================================
# SINGLETON & INITIALIZATION
# =============================================================================

_enhanced_learning_instance: Optional[EnhancedProactiveLearning] = None


def get_enhanced_proactive_learning(
    oracle_hub=None,
    enhanced_memory=None,
    reverse_knn=None,
    llm_client=None
) -> EnhancedProactiveLearning:
    """Get singleton enhanced proactive learning instance."""
    global _enhanced_learning_instance
    
    if _enhanced_learning_instance is None:
        _enhanced_learning_instance = EnhancedProactiveLearning(
            oracle_hub=oracle_hub,
            enhanced_memory=enhanced_memory,
            reverse_knn=reverse_knn,
            llm_client=llm_client
        )
    
    return _enhanced_learning_instance


async def initialize_enhanced_learning():
    """Initialize enhanced learning with all connections."""
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        
        hub = get_oracle_hub()
        memory = get_enhanced_oracle_memory()
        rknn = get_reverse_knn_learning(oracle_hub=hub)
        
        learning = get_enhanced_proactive_learning(
            oracle_hub=hub,
            enhanced_memory=memory,
            reverse_knn=rknn
        )
        
        learning.start_continuous_learning()
        
        logger.info("[ENHANCED-LEARNING] Fully initialized and running")
        return learning
        
    except Exception as e:
        logger.error(f"[ENHANCED-LEARNING] Initialization failed: {e}")
        return None
