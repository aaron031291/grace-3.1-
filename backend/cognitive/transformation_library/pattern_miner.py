import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from cognitive.transformation_library.outcome_ledger import OutcomeLedger, TransformationOutcome
from cognitive.magma_memory_system import MagmaLayer, MagmaMemorySystem
from cognitive.memory_mesh_integration import MemoryMeshIntegration
class TransformationPatternMiner:
    logger = logging.getLogger(__name__)
    """
    Pattern miner that discovers new rules from successful transforms.
    
    Features:
    1. Clusters successful diffs from Outcome Ledger
    2. Detects recurring manual edits (not yet automated)
    3. Proposes new rules or refinements
    4. Generates "why this rule exists" documentation
    """

    def __init__(
        self,
        session: Session,
        outcome_ledger: OutcomeLedger,
        magma_memory: Optional[MagmaMemorySystem] = None,
        memory_mesh: Optional[MemoryMeshIntegration] = None
    ):
        """
        Initialize Pattern Miner.
        
        Args:
            session: Database session
            outcome_ledger: Outcome ledger
            magma_memory: Magma memory system (optional)
            memory_mesh: Memory mesh integration (optional)
        """
        self.session = session
        self.outcome_ledger = outcome_ledger
        self.magma_memory = magma_memory
        self.memory_mesh = memory_mesh
        
        logger.info("[PATTERN-MINER] Initialized")

    def mine_patterns(self) -> Dict[str, Any]:
        """
        Mine patterns from successful transforms.
        
        Returns:
            Dictionary with discovered patterns and proposals
        """
        logger.info("[PATTERN-MINER] Starting pattern mining")
        
        results = {
            "clusters": [],
            "manual_edits": [],
            "rule_proposals": [],
            "rule_refinements": [],
            "statistics": {}
        }
        
        try:
            # 1. Get successful transforms from Outcome Ledger (Mantle/Core layers)
            successful_transforms = self.outcome_ledger.get_by_layer(
                layers=[MagmaLayer.MANTLE, MagmaLayer.CORE],
                min_crystallized=0.7,
                limit=1000
            )
            
            logger.info(f"[PATTERN-MINER] Found {len(successful_transforms)} successful transforms")
            
            if not successful_transforms:
                logger.info("[PATTERN-MINER] No successful transforms to mine")
                return results
            
            # 2. Cluster by AST pattern signature
            clusters = self._cluster_transforms(successful_transforms)
            results["clusters"] = clusters
            
            logger.info(f"[PATTERN-MINER] Discovered {len(clusters)} clusters")
            
            # 3. Detect recurring manual edits (compare with manual code changes)
            manual_edits = self._detect_manual_patterns()
            results["manual_edits"] = manual_edits
            
            logger.info(f"[PATTERN-MINER] Found {len(manual_edits)} manual edit patterns")
            
            # 4. Generate rule proposals from clusters and manual edits
            rule_proposals = self._generate_rule_proposals(clusters, manual_edits)
            results["rule_proposals"] = rule_proposals
            
            logger.info(f"[PATTERN-MINER] Generated {len(rule_proposals)} rule proposals")
            
            # 5. Generate rule refinements from clusters
            rule_refinements = self._generate_rule_refinements(clusters)
            results["rule_refinements"] = rule_refinements
            
            logger.info(f"[PATTERN-MINER] Generated {len(rule_refinements)} rule refinements")
            
            # 6. Store proposals in learning memory
            self._store_proposals_in_memory(rule_proposals, rule_refinements)
            
            # Statistics
            results["statistics"] = {
                "successful_transforms": len(successful_transforms),
                "clusters_discovered": len(clusters),
                "manual_edits_found": len(manual_edits),
                "rule_proposals_generated": len(rule_proposals),
                "rule_refinements_generated": len(rule_refinements)
            }
            
            logger.info("[PATTERN-MINER] Pattern mining complete")
        
        except Exception as e:
            logger.error(f"[PATTERN-MINER] Error during pattern mining: {e}")
            results["error"] = str(e)
        
        return results

    def _cluster_transforms(
        self,
        transforms: List[TransformationOutcome]
    ) -> List[Dict[str, Any]]:
        """Cluster transforms by AST pattern signature."""
        # Group by pattern signature
        clusters = defaultdict(list)
        
        for transform in transforms:
            signature = transform.ast_pattern_signature
            clusters[signature].append(transform)
        
        # Convert to cluster list
        cluster_list = []
        
        for signature, transform_list in clusters.items():
            if len(transform_list) >= 2:  # At least 2 similar transforms
                cluster_list.append({
                    "pattern_signature": signature,
                    "count": len(transform_list),
                    "rule_ids": list(set(t.rule_id for t in transform_list)),
                    "avg_crystallized": sum(t.crystallized for t in transform_list) / len(transform_list),
                    "transforms": [t.id for t in transform_list[:5]]  # First 5
                })
        
        # Sort by count (most frequent first)
        cluster_list.sort(key=lambda c: c["count"], reverse=True)
        
        return cluster_list

    def _detect_manual_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect recurring manual edits not yet automated.
        
        This would compare manual code changes (from git history, etc.)
        with existing transformations to find patterns that should be automated.
        """
        # Placeholder implementation
        # In practice, this would:
        # 1. Analyze git commits for manual code changes
        # 2. Extract AST patterns from diffs
        # 3. Compare with existing transformation outcomes
        # 4. Identify recurring patterns not yet covered by rules
        
        manual_edits = []
        
        # TODO: Implement git diff analysis
        # For now, return empty list
        
        return manual_edits

    def _generate_rule_proposals(
        self,
        clusters: List[Dict[str, Any]],
        manual_edits: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate new rule proposals from clusters and manual edits."""
        proposals = []
        
        # Generate proposals from clusters with high frequency but no existing rule
        for cluster in clusters:
            if cluster["count"] >= 5:  # High frequency
                # Check if there's already a rule for this pattern
                # For now, propose a new rule
                proposal = {
                    "pattern_signature": cluster["pattern_signature"],
                    "frequency": cluster["count"],
                    "confidence": min(1.0, cluster["count"] / 10.0),  # Scale confidence
                    "proposed_rule": {
                        "id": f"auto_discovered_{cluster['pattern_signature'][:8]}",
                        "version": "1.0",
                        "pattern": {
                            "type": "ast",
                            "match": "TODO: Extract from cluster",
                            "language": "python"
                        },
                        "rewrite": {
                            "template": "TODO: Extract from diffs",
                            "preserve": []
                        },
                        "constraints": {
                            "pre": [],
                            "post": []
                        },
                        "proof_required": [],
                        "side_effects": [],
                        "description": f"Auto-discovered rule from {cluster['count']} successful transforms"
                    },
                    "why_exists": self._generate_why_documentation(cluster)
                }
                proposals.append(proposal)
        
        # Generate proposals from manual edits
        for edit in manual_edits:
            proposal = {
                "pattern_signature": edit.get("pattern_signature", "unknown"),
                "frequency": edit.get("frequency", 1),
                "confidence": 0.6,  # Manual edits are less certain
                "proposed_rule": {
                    "id": f"manual_edit_{edit.get('pattern_signature', 'unknown')[:8]}",
                    "version": "1.0",
                    "pattern": edit.get("pattern", {}),
                    "rewrite": edit.get("rewrite", {}),
                    "constraints": {"pre": [], "post": []},
                    "proof_required": [],
                    "side_effects": [],
                    "description": f"Rule proposed from {edit.get('frequency', 1)} manual edits"
                },
                "why_exists": f"Recurring manual edit pattern detected {edit.get('frequency', 1)} times"
            }
            proposals.append(proposal)
        
        # Sort by confidence
        proposals.sort(key=lambda p: p["confidence"], reverse=True)
        
        return proposals

    def _generate_rule_refinements(
        self,
        clusters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate refinements for existing rules."""
        refinements = []
        
        # Analyze clusters to find patterns that could improve existing rules
        # For example, if a rule has variations that aren't handled
        
        # Placeholder implementation
        # In practice, this would:
        # 1. Group transforms by existing rule_id
        # 2. Analyze variations in patterns
        # 3. Propose refinements to handle edge cases
        
        return refinements

    def _generate_why_documentation(self, cluster: Dict[str, Any]) -> str:
        """Generate 'why this rule exists' documentation."""
        rule_ids = cluster.get("rule_ids", [])
        count = cluster.get("count", 0)
        avg_crystallized = cluster.get("avg_crystallized", 0.0)
        
        doc = f"""
This rule was discovered through pattern mining from {count} successful transformations.

Pattern Signature: {cluster.get('pattern_signature', 'unknown')[:16]}...
Rules Involved: {', '.join(rule_ids) if rule_ids else 'Auto-discovered'}
Average Crystallization: {avg_crystallized:.2f}

This pattern appears frequently in successful transforms, indicating it's a common
and valuable transformation that should be automated.
        """.strip()
        
        return doc

    def _store_proposals_in_memory(
        self,
        rule_proposals: List[Dict[str, Any]],
        rule_refinements: List[Dict[str, Any]]
    ):
        """Store proposals in learning memory for review."""
        if not self.memory_mesh:
            return
        
        try:
            # Store rule proposals
            for proposal in rule_proposals:
                self.memory_mesh.ingest_learning_experience(
                    experience_type="rule_proposal",
                    context={
                        "pattern": proposal.get("pattern_signature"),
                        "frequency": proposal.get("frequency", 0),
                        "confidence": proposal.get("confidence", 0.0)
                    },
                    action_taken={
                        "proposed_rule": proposal.get("proposed_rule", {}),
                        "why_exists": proposal.get("why_exists", "")
                    },
                    outcome={
                        "quality_score": proposal.get("confidence", 0.0),
                        "status": "proposed"
                    },
                    source="pattern_miner",
                    genesis_key_id=None
                )
            
            logger.info(
                f"[PATTERN-MINER] Stored {len(rule_proposals)} proposals in memory mesh"
            )
        
        except Exception as e:
            logger.warning(f"[PATTERN-MINER] Error storing proposals in memory: {e}")
