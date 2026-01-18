"""
Layer 4 Integration Hub: Wiring Neuro-Symbolic Intelligence to Lower Layers

This module connects Layer 4 (Neuro-Symbolic) to:
- Layer 3 (Quorum Governance) - Export validated patterns as trusted
- Layer 2 (Connections/Understanding) - Feed insights to knowledge graph
- Layer 1 (Facts/Templates) - Store synthesized programs and concepts

Data Flow:
    Layer 4 ──▶ Validated Patterns ──▶ Layer 3 Whitelist
       │
       ├──▶ Cross-Domain Insights ──▶ Layer 2 Knowledge Graph
       │
       └──▶ Synthesized Programs ──▶ Layer 1 Templates
           Learned Concepts ──▶ Layer 1 Facts

Upward Flow (Layer 4 receives from):
    - Self-healing events → Pattern learning
    - Code analysis → Template extraction
    - Error logs → Abductive reasoning
    - User feedback → Concept refinement
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
import os

logger = logging.getLogger(__name__)


class Layer4IntegrationHub:
    """
    Integration hub connecting Layer 4 to all other layers.
    
    This is the central nervous system for neuro-symbolic intelligence,
    routing learned patterns to where they're needed.
    """
    
    def __init__(self, session=None):
        self.session = session
        
        # Layer 4 components (lazy loaded)
        self._layer4_base = None
        self._layer4_advanced = None
        self._layer4_frontier = None
        
        # Connected layers (lazy loaded)
        self._layer3_governance = None
        self._layer2_connections = None
        self._layer1_integration = None
        
        # Integration paths
        self.integration_base = Path("knowledge_base/layer_4_integration")
        self.integration_base.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            "patterns_exported_to_l3": 0,
            "insights_sent_to_l2": 0,
            "programs_stored_in_l1": 0,
            "concepts_stored_in_l1": 0,
            "events_received": 0,
        }
        
        logger.info("[L4-INTEGRATION] Hub initialized")
    
    # =========================================================================
    # LAYER 4 COMPONENT ACCESS
    # =========================================================================
    
    @property
    def layer4_base(self):
        """Get base Layer 4 (recursive pattern learner)."""
        if self._layer4_base is None:
            try:
                from ml_intelligence.layer4_recursive_pattern_learner import (
                    get_layer4_recursive_learner
                )
                self._layer4_base = get_layer4_recursive_learner(
                    governance_engine=self.layer3_governance,
                    learning_memory=self._get_learning_memory(),
                )
                logger.info("[L4-INTEGRATION] Base Layer 4 connected")
            except Exception as e:
                logger.error(f"[L4-INTEGRATION] Base Layer 4 failed: {e}")
        return self._layer4_base
    
    @property
    def layer4_advanced(self):
        """Get advanced Layer 4."""
        if self._layer4_advanced is None:
            try:
                from ml_intelligence.layer4_advanced_neuro_symbolic import (
                    get_advanced_layer4
                )
                self._layer4_advanced = get_advanced_layer4(
                    base_layer4=self.layer4_base
                )
                logger.info("[L4-INTEGRATION] Advanced Layer 4 connected")
            except Exception as e:
                logger.error(f"[L4-INTEGRATION] Advanced Layer 4 failed: {e}")
        return self._layer4_advanced
    
    @property
    def layer4_frontier(self):
        """Get frontier Layer 4 (GPU)."""
        if self._layer4_frontier is None:
            try:
                from ml_intelligence.layer4_frontier_reasoning import (
                    get_frontier_layer4
                )
                self._layer4_frontier = get_frontier_layer4()
                logger.info("[L4-INTEGRATION] Frontier Layer 4 connected")
            except Exception as e:
                logger.error(f"[L4-INTEGRATION] Frontier Layer 4 failed: {e}")
        return self._layer4_frontier
    
    # =========================================================================
    # LAYER 3 INTEGRATION (Governance)
    # =========================================================================
    
    @property
    def layer3_governance(self):
        """Get Layer 3 governance engine."""
        if self._layer3_governance is None:
            try:
                from governance.quorum_governance import get_quorum_governance
                self._layer3_governance = get_quorum_governance(self.session)
                logger.info("[L4-INTEGRATION] Layer 3 Governance connected")
            except Exception as e:
                logger.warning(f"[L4-INTEGRATION] Layer 3 not available: {e}")
        return self._layer3_governance
    
    def export_pattern_to_governance(
        self,
        pattern_id: str,
        pattern_data: Dict[str, Any],
        trust_score: float,
    ) -> bool:
        """
        Export a validated pattern to Layer 3 governance.
        
        High-trust patterns (≥0.9) go to whitelist (100% trusted).
        Lower trust patterns are recorded for KPI tracking.
        """
        if not self.layer3_governance:
            logger.warning("[L4-INTEGRATION] No Layer 3 connection, caching locally")
            self._cache_for_layer3(pattern_id, pattern_data, trust_score)
            return False
        
        try:
            gov_data = {
                "type": "layer4_pattern",
                "pattern_id": pattern_id,
                "trust_score": trust_score,
                "data": pattern_data,
                "exported_at": datetime.utcnow().isoformat(),
            }
            
            # High trust → Whitelist
            if trust_score >= 0.9:
                if hasattr(self.layer3_governance, 'add_to_whitelist'):
                    self.layer3_governance.add_to_whitelist(
                        source=f"layer4_{pattern_id[:8]}",
                        data=gov_data,
                    )
                    logger.info(f"[L4→L3] Pattern {pattern_id[:8]} added to whitelist")
            
            # Record KPI
            if hasattr(self.layer3_governance, 'record_component_outcome'):
                domain = pattern_data.get("source_domain", "unknown")
                self.layer3_governance.record_component_outcome(
                    component_id=f"layer4_{domain}",
                    success=True,
                    meets_grace_standard=trust_score >= 0.7,
                    meets_user_standard=trust_score >= 0.6,
                    weight=1.0,
                )
            
            self.stats["patterns_exported_to_l3"] += 1
            return True
            
        except Exception as e:
            logger.error(f"[L4→L3] Export failed: {e}")
            return False
    
    def _cache_for_layer3(self, pattern_id: str, data: Dict, trust: float):
        """Cache pattern for later Layer 3 export."""
        cache_file = self.integration_base / "l3_pending.json"
        
        pending = []
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                pending = json.load(f)
        
        pending.append({
            "pattern_id": pattern_id,
            "data": data,
            "trust_score": trust,
            "cached_at": datetime.utcnow().isoformat(),
        })
        
        with open(cache_file, 'w') as f:
            json.dump(pending[-1000:], f)  # Keep last 1000
    
    # =========================================================================
    # LAYER 2 INTEGRATION (Connections/Understanding)
    # =========================================================================
    
    @property
    def layer2_connections(self):
        """Get Layer 2 connections/knowledge graph."""
        if self._layer2_connections is None:
            try:
                from genesis.layer_intelligence import get_intelligence_layer
                self._layer2_connections = get_intelligence_layer(self.session)
                logger.info("[L4-INTEGRATION] Layer 2 Connections connected")
            except Exception as e:
                logger.warning(f"[L4-INTEGRATION] Layer 2 not available: {e}")
        return self._layer2_connections
    
    def send_insight_to_layer2(
        self,
        insight_type: str,
        insight_data: Dict[str, Any],
        source_patterns: List[str],
    ) -> bool:
        """
        Send cross-domain insight to Layer 2 knowledge graph.
        
        Insights include:
        - Cross-domain pattern transfers
        - Analogical mappings
        - Causal relationships
        """
        try:
            insight = {
                "type": insight_type,
                "data": insight_data,
                "source_patterns": source_patterns,
                "created_at": datetime.utcnow().isoformat(),
                "layer": 4,
            }
            
            # Store in Layer 2 if available
            if self.layer2_connections:
                if hasattr(self.layer2_connections, 'add_knowledge'):
                    self.layer2_connections.add_knowledge(
                        category="layer4_insight",
                        data=insight,
                    )
                    logger.info(f"[L4→L2] Insight '{insight_type}' sent")
            
            # Also store locally
            insights_file = self.integration_base / "l2_insights.json"
            insights = []
            if insights_file.exists():
                with open(insights_file, 'r') as f:
                    insights = json.load(f)
            
            insights.append(insight)
            
            with open(insights_file, 'w') as f:
                json.dump(insights[-500:], f)  # Keep last 500
            
            self.stats["insights_sent_to_l2"] += 1
            return True
            
        except Exception as e:
            logger.error(f"[L4→L2] Insight failed: {e}")
            return False
    
    def send_analogy_to_layer2(
        self,
        source_domain: str,
        target_domain: str,
        mapping: Dict[str, str],
        score: float,
    ) -> bool:
        """Send analogical mapping to Layer 2."""
        return self.send_insight_to_layer2(
            insight_type="analogical_mapping",
            insight_data={
                "source_domain": source_domain,
                "target_domain": target_domain,
                "mapping": mapping,
                "score": score,
            },
            source_patterns=[],
        )
    
    # =========================================================================
    # LAYER 1 INTEGRATION (Facts/Templates)
    # =========================================================================
    
    @property
    def layer1_integration(self):
        """Get Layer 1 integration."""
        if self._layer1_integration is None:
            try:
                from genesis.layer1_integration import Layer1Integration
                self._layer1_integration = Layer1Integration(self.session)
                logger.info("[L4-INTEGRATION] Layer 1 connected")
            except Exception as e:
                logger.warning(f"[L4-INTEGRATION] Layer 1 not available: {e}")
        return self._layer1_integration
    
    def store_synthesized_program(
        self,
        program_id: str,
        code: str,
        spec: Dict[str, Any],
        confidence: float,
    ) -> bool:
        """
        Store a synthesized program in Layer 1 as a template.
        """
        program_data = {
            "program_id": program_id,
            "code": code,
            "spec": spec,
            "confidence": confidence,
            "synthesized_at": datetime.utcnow().isoformat(),
            "source": "layer4_neural_synthesis",
        }
        
        # Try to store in Layer 1 learning memory
        try:
            if self.layer1_integration:
                if hasattr(self.layer1_integration, 'process_learning_memory'):
                    self.layer1_integration.process_learning_memory(
                        learning_type="synthesized_program",
                        learning_data=program_data,
                        metadata={"source": "layer4"},
                    )
                    logger.info(f"[L4→L1] Program {program_id[:8]} stored in Layer 1")
        except Exception as e:
            logger.warning(f"[L4→L1] Layer 1 storage failed (will store locally): {e}")
        
        # Always store locally as backup
        try:
            programs_dir = self.integration_base / "synthesized_programs"
            programs_dir.mkdir(parents=True, exist_ok=True)
            
            with open(programs_dir / f"{program_id}.json", 'w') as f:
                json.dump(program_data, f, indent=2)
            
            self.stats["programs_stored_in_l1"] += 1
            return True
            
        except Exception as e:
            logger.error(f"[L4→L1] Program storage failed: {e}")
            return False
    
    def store_learned_concept(
        self,
        concept_name: str,
        concept_data: Dict[str, Any],
    ) -> bool:
        """
        Store a learned concept in Layer 1 as a fact.
        """
        concept = {
            "name": concept_name,
            "data": concept_data,
            "learned_at": datetime.utcnow().isoformat(),
            "source": "layer4_concept_learner",
        }
        
        # Try to store in Layer 1
        try:
            if self.layer1_integration:
                if hasattr(self.layer1_integration, 'process_learning_memory'):
                    self.layer1_integration.process_learning_memory(
                        learning_type="learned_concept",
                        learning_data=concept,
                        metadata={"source": "layer4"},
                    )
                    logger.info(f"[L4→L1] Concept '{concept_name}' stored in Layer 1")
        except Exception as e:
            logger.warning(f"[L4→L1] Layer 1 storage failed (will store locally): {e}")
        
        # Always store locally as backup
        try:
            concepts_dir = self.integration_base / "learned_concepts"
            concepts_dir.mkdir(parents=True, exist_ok=True)
            
            with open(concepts_dir / f"{concept_name}.json", 'w') as f:
                json.dump(concept, f, indent=2)
            
            self.stats["concepts_stored_in_l1"] += 1
            return True
            
        except Exception as e:
            logger.error(f"[L4→L1] Concept storage failed: {e}")
            return False
    
    # =========================================================================
    # UPWARD FLOW (Receiving from other systems)
    # =========================================================================
    
    def receive_healing_event(
        self,
        error_type: str,
        error_content: str,
        fix_applied: str,
        success: bool,
    ) -> Dict[str, Any]:
        """
        Receive a healing event and learn from it.
        
        This feeds into:
        - Pattern learning (error → fix patterns)
        - Abductive reasoning (why did this error occur?)
        - Concept formation (error categories)
        """
        self.stats["events_received"] += 1
        
        result = {
            "patterns_learned": 0,
            "hypotheses_generated": 0,
        }
        
        try:
            # Feed to base Layer 4 for pattern learning
            if self.layer4_base:
                from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
                
                cycle = self.layer4_base.run_recursive_cycle(
                    domain=PatternDomain.HEALING,
                    data=[{
                        "text": f"Error: {error_type}\n{error_content}\nFix: {fix_applied}",
                        "success": success,
                    }],
                    max_iterations=1,
                )
                result["patterns_learned"] = cycle.patterns_validated
            
            # Feed to frontier for abductive reasoning
            if self.layer4_frontier and not success:
                self.layer4_frontier.abductive.add_observation({
                    "error_type": error_type,
                    "content": error_content[:200],
                })
                result["hypotheses_generated"] = 1
            
        except Exception as e:
            logger.error(f"[L4-INTEGRATION] Healing event failed: {e}")
        
        return result
    
    def receive_code_analysis(
        self,
        file_path: str,
        analysis_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Receive code analysis results and extract patterns.
        """
        self.stats["events_received"] += 1
        
        result = {"patterns_extracted": 0}
        
        try:
            if self.layer4_base:
                from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
                
                cycle = self.layer4_base.run_recursive_cycle(
                    domain=PatternDomain.CODE,
                    data=[{
                        "text": f"File: {file_path}\n{json.dumps(analysis_data)}",
                        "file": file_path,
                    }],
                    max_iterations=1,
                )
                result["patterns_extracted"] = cycle.patterns_validated
                
        except Exception as e:
            logger.error(f"[L4-INTEGRATION] Code analysis failed: {e}")
        
        return result
    
    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================
    
    def sync_pending_exports(self) -> Dict[str, int]:
        """Sync any pending exports to lower layers."""
        synced = {"l3": 0, "l2": 0, "l1": 0}
        
        # Sync Layer 3 pending
        cache_file = self.integration_base / "l3_pending.json"
        if cache_file.exists() and self.layer3_governance:
            try:
                with open(cache_file, 'r') as f:
                    pending = json.load(f)
                
                for item in pending:
                    if self.export_pattern_to_governance(
                        item["pattern_id"],
                        item["data"],
                        item["trust_score"],
                    ):
                        synced["l3"] += 1
                
                # Clear synced items
                os.remove(cache_file)
                
            except Exception as e:
                logger.error(f"[L4-INTEGRATION] L3 sync failed: {e}")
        
        return synced
    
    def run_learning_cycle(
        self,
        domain: str,
        data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Run a full learning cycle and propagate results to lower layers.
        """
        results = {
            "patterns_discovered": 0,
            "patterns_validated": 0,
            "exported_to_l3": 0,
            "insights_to_l2": 0,
        }
        
        try:
            from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
            
            domain_enum = PatternDomain(domain.lower())
            
            # Run cycle
            cycle = self.layer4_base.run_recursive_cycle(
                domain=domain_enum,
                data=data,
                max_iterations=3,
            )
            
            results["patterns_discovered"] = cycle.patterns_discovered
            results["patterns_validated"] = cycle.patterns_validated
            
            # Export high-trust patterns to Layer 3
            for pattern in self.layer4_base.get_patterns_for_domain(domain_enum, min_trust=0.7):
                if self.export_pattern_to_governance(
                    pattern.pattern_id,
                    pattern.to_dict(),
                    pattern.trust_score,
                ):
                    results["exported_to_l3"] += 1
            
            # Send cross-domain insights to Layer 2
            if cycle.patterns_transferred > 0:
                self.send_insight_to_layer2(
                    insight_type="cross_domain_transfer",
                    insight_data={
                        "source_domain": domain,
                        "patterns_transferred": cycle.patterns_transferred,
                        "domains_touched": [d.value for d in cycle.domains_touched],
                    },
                    source_patterns=[],
                )
                results["insights_to_l2"] += 1
            
        except Exception as e:
            logger.error(f"[L4-INTEGRATION] Learning cycle failed: {e}")
        
        return results
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _get_learning_memory(self):
        """Get learning memory manager."""
        try:
            from cognitive.learning_memory import get_learning_memory
            return get_learning_memory(self.session)
        except:
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration hub status."""
        return {
            "layer4_base_connected": self._layer4_base is not None,
            "layer4_advanced_connected": self._layer4_advanced is not None,
            "layer4_frontier_connected": self._layer4_frontier is not None,
            "layer3_connected": self._layer3_governance is not None,
            "layer2_connected": self._layer2_connections is not None,
            "layer1_connected": self._layer1_integration is not None,
            "stats": self.stats,
        }


# Factory function
_integration_hub = None


def get_layer4_integration(session=None) -> Layer4IntegrationHub:
    """Get Layer 4 integration hub singleton."""
    global _integration_hub
    
    if _integration_hub is None:
        _integration_hub = Layer4IntegrationHub(session)
    
    return _integration_hub
