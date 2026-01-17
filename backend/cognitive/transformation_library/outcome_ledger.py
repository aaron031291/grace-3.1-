import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from cognitive.magma_memory_system import MagmaMemorySystem, MagmaLayer
class TransformationOutcome:
    logger = logging.getLogger(__name__)
    """A transformation outcome record."""
    rule_id: str
    rule_version: str
    ast_pattern_signature: str
    before_code: str
    after_code: str
    diff_summary: str
    proof_results: Dict[str, str]
    rollback_status: str  # "available", "committed", "rolled_back"
    time_to_merge: Optional[float] = None  # seconds if PR-based
    magma_layer: str = "surface"  # "surface", "mantle", "core"
    temperature: float = 0.85  # Activity metric (0-1)
    crystallized: float = 0.30  # Validation metric (0-1)
    genesis_key_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    file_path: Optional[str] = None
    user_id: Optional[str] = None
    id: Optional[str] = None  # Outcome ID

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransformationOutcome":
        """Create from dictionary."""
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class OutcomeLedger:
    """
    Magma-backed outcome ledger for transformation logging.
    
    Features:
    - Immutable logging of all transforms
    - Integration with Magma memory layers
    - Link to Genesis Keys for provenance
    - Pattern signature tracking for clustering
    """

    def __init__(
        self,
        session: Session,
        magma_memory: Optional[MagmaMemorySystem] = None
    ):
        """
        Initialize Outcome Ledger.
        
        Args:
            session: Database session
            magma_memory: Magma memory system (optional)
        """
        self.session = session
        self.magma_memory = magma_memory
        
        # In-memory store (can be persisted to database)
        self._outcomes: Dict[str, TransformationOutcome] = {}
        
        logger.info("[OUTCOME-LEDGER] Initialized")

    def log_transformation(
        self,
        rule_id: str,
        rule_version: str,
        ast_pattern_signature: str,
        before_code: str,
        after_code: str,
        diff_summary: str,
        proof_results: Dict[str, str],
        rollback_status: str = "available",
        time_to_merge: Optional[float] = None,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a transformation outcome.
        
        Args:
            rule_id: Rule identifier
            rule_version: Rule version
            ast_pattern_signature: Signature of matched AST pattern
            before_code: Original code
            after_code: Transformed code
            diff_summary: Summary of changes
            proof_results: Proof verification results
            rollback_status: Rollback status
            time_to_merge: Time to merge (if PR-based)
            file_path: File path
            user_id: User ID
            genesis_key_id: Genesis Key ID
        
        Returns:
            Outcome record with ID
        """
        timestamp = datetime.utcnow()
        
        # Generate outcome ID
        outcome_id = self._generate_outcome_id(
            rule_id=rule_id,
            ast_pattern_signature=ast_pattern_signature,
            timestamp=timestamp
        )
        
        # Classify into Magma layer (initially Surface)
        magma_layer, temperature, crystallized = self._classify_layer(
            proof_results=proof_results,
            rollback_status=rollback_status
        )
        
        # Create outcome record
        outcome = TransformationOutcome(
            id=outcome_id,
            rule_id=rule_id,
            rule_version=rule_version,
            ast_pattern_signature=ast_pattern_signature,
            before_code=before_code,
            after_code=after_code,
            diff_summary=diff_summary,
            proof_results=proof_results,
            rollback_status=rollback_status,
            time_to_merge=time_to_merge,
            magma_layer=magma_layer.value if isinstance(magma_layer, MagmaLayer) else magma_layer,
            temperature=temperature,
            crystallized=crystallized,
            genesis_key_id=genesis_key_id,
            timestamp=timestamp,
            file_path=file_path,
            user_id=user_id
        )
        
        # Store outcome
        self._outcomes[outcome_id] = outcome
        
        # Store in Magma memory if available
        if self.magma_memory:
            self._store_in_magma(outcome)
        
        logger.info(
            f"[OUTCOME-LEDGER] Logged transformation: {rule_id} "
            f"({magma_layer}, {outcome_id[:8]})"
        )
        
        return outcome.to_dict()

    def _generate_outcome_id(
        self,
        rule_id: str,
        ast_pattern_signature: str,
        timestamp: datetime
    ) -> str:
        """Generate unique outcome ID."""
        combined = f"{rule_id}:{ast_pattern_signature}:{timestamp.isoformat()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def _classify_layer(
        self,
        proof_results: Dict[str, str],
        rollback_status: str
    ) -> tuple[MagmaLayer, float, float]:
        """Classify outcome into Magma layer."""
        # Initially classify as Surface (hot, fluid)
        layer = MagmaLayer.SURFACE
        
        # Calculate temperature (activity)
        temperature = 0.85  # Recent transforms are hot
        
        # Calculate crystallized (validation)
        proof_count = len(proof_results)
        verified_count = sum(1 for status in proof_results.values() if status == "verified")
        
        if proof_count > 0:
            crystallized = verified_count / proof_count
        else:
            crystallized = 0.30  # Default for new transforms
        
        # If highly validated and committed, move toward Mantle
        if crystallized >= 0.7 and rollback_status == "committed":
            layer = MagmaLayer.MANTLE
        
        # If extremely validated and used multiple times, move toward Core
        # (This would be updated by pattern miner after multiple successful uses)
        if crystallized >= 0.9:
            layer = MagmaLayer.MANTLE  # One step toward Core
        
        return layer, temperature, crystallized

    def _store_in_magma(self, outcome: TransformationOutcome):
        """Store outcome in Magma memory system."""
        if not self.magma_memory:
            return
        
        try:
            # Convert outcome to memory format
            memory_dict = outcome.to_dict()
            
            # Classify layer using Magma system
            layer, temperature, crystallized = self.magma_memory.classify_memory_layer(
                memory=memory_dict,
                access_count=0,
                last_accessed=outcome.timestamp
            )
            
            # Update outcome with Magma classification
            outcome.magma_layer = layer.value
            outcome.temperature = temperature
            outcome.crystallized = crystallized
            
            logger.debug(
                f"[OUTCOME-LEDGER] Stored in Magma: {outcome.id[:8]} "
                f"-> {layer.value} (temp={temperature:.2f}, cryst={crystallized:.2f})"
            )
        
        except Exception as e:
            logger.warning(f"[OUTCOME-LEDGER] Error storing in Magma: {e}")

    def get_outcome(self, outcome_id: str) -> Optional[TransformationOutcome]:
        """Get outcome by ID."""
        return self._outcomes.get(outcome_id)

    def get_by_layer(
        self,
        layers: List[MagmaLayer],
        min_crystallized: float = 0.0,
        limit: int = 100
    ) -> List[TransformationOutcome]:
        """Get outcomes by Magma layer."""
        results = []
        
        for outcome in self._outcomes.values():
            outcome_layer = MagmaLayer(outcome.magma_layer) if isinstance(outcome.magma_layer, str) else outcome.magma_layer
            
            if outcome_layer in layers and outcome.crystallized >= min_crystallized:
                results.append(outcome)
        
        # Sort by crystallized (highest first)
        results.sort(key=lambda o: o.crystallized, reverse=True)
        
        return results[:limit]

    def get_by_rule(
        self,
        rule_id: str,
        rule_version: Optional[str] = None,
        limit: int = 100
    ) -> List[TransformationOutcome]:
        """Get outcomes by rule ID and optional version."""
        results = []
        
        for outcome in self._outcomes.values():
            if outcome.rule_id == rule_id:
                if rule_version is None or outcome.rule_version == rule_version:
                    results.append(outcome)
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda o: o.timestamp or datetime.min, reverse=True)
        
        return results[:limit]

    def update_rollback_status(
        self,
        outcome_id: str,
        rollback_status: str
    ) -> bool:
        """Update rollback status of an outcome."""
        outcome = self._outcomes.get(outcome_id)
        if not outcome:
            return False
        
        outcome.rollback_status = rollback_status
        
        # Reclassify layer if committed
        if rollback_status == "committed":
            if outcome.crystallized >= 0.7:
                outcome.magma_layer = MagmaLayer.MANTLE.value
            # Re-store in Magma
            if self.magma_memory:
                self._store_in_magma(outcome)
        
        logger.info(f"[OUTCOME-LEDGER] Updated rollback status: {outcome_id[:8]} -> {rollback_status}")
        
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get ledger statistics."""
        total = len(self._outcomes)
        
        by_layer = {
            "surface": 0,
            "mantle": 0,
            "core": 0
        }
        
        by_status = {
            "available": 0,
            "committed": 0,
            "rolled_back": 0
        }
        
        for outcome in self._outcomes.values():
            layer = outcome.magma_layer
            if layer in by_layer:
                by_layer[layer] += 1
            
            status = outcome.rollback_status
            if status in by_status:
                by_status[status] += 1
        
        return {
            "total_outcomes": total,
            "by_layer": by_layer,
            "by_status": by_status,
            "avg_crystallized": sum(o.crystallized for o in self._outcomes.values()) / total if total > 0 else 0.0
        }
