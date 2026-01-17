"""
Federated Learning System for Grace

Enables federated learning across:
1. Multiple sandbox instances (syntax, logic, performance, security, architecture)
2. Multiple Grace deployments (if multiple instances exist)
3. Domain-specific model training with aggregated updates

Benefits:
- Privacy-preserving (no raw data sharing)
- Distributed learning (multiple clients)
- Model aggregation (shared knowledge)
- Efficient knowledge transfer
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import hashlib

logger = logging.getLogger(__name__)


class FederatedClientType(str, Enum):
    """Type of federated learning client."""
    SANDBOX_INSTANCE = "sandbox_instance"  # Sandbox training instance
    GRACE_DEPLOYMENT = "grace_deployment"  # Separate Grace deployment
    DOMAIN_SPECIALIST = "domain_specialist"  # Domain-specific specialist


@dataclass
class ModelUpdate:
    """A model update from a federated client."""
    client_id: str
    client_type: FederatedClientType
    domain: str  # Problem perspective/domain
    update_id: str
    model_weights: Dict[str, Any]  # Learned patterns/weights
    patterns_learned: List[str]  # Patterns learned
    topics_learned: List[Dict[str, Any]]  # Topics learned
    success_rate: float
    files_processed: int
    files_fixed: int
    trust_score: float  # Trust in this client's updates
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AggregatedModel:
    """Aggregated model from federated updates."""
    domain: str
    aggregated_patterns: List[str]
    aggregated_topics: List[Dict[str, Any]]
    average_success_rate: float
    total_files_processed: int
    total_files_fixed: int
    client_count: int
    last_updated: datetime
    model_version: int


class FederatedLearningSystem:
    """
    Federated Learning System for Grace.
    
    Enables:
    1. Multi-instance federated learning (sandbox instances as clients)
    2. Cross-deployment learning (multiple Grace instances)
    3. Domain-specific model aggregation
    4. Privacy-preserving knowledge sharing
    """
    
    def __init__(
        self,
        server_id: str = "grace_federated_server",
        enable_cross_deployment: bool = False,
        learning_memory_manager=None,
        llm_orchestrator=None,
        genesis_service=None,
        session=None
    ):
        """Initialize Federated Learning System (Grace-Aligned)."""
        self.server_id = server_id
        self.enable_cross_deployment = enable_cross_deployment
        
        # Learning memory and LLM integration
        self.learning_memory = learning_memory_manager
        self.llm_orchestrator = llm_orchestrator
        
        # Genesis Key service for Grace-aligned tracking
        self.genesis_service = genesis_service
        self.session = session
        
        # Grace-aligned components
        self.grace_invariants_enabled = True
        self.trust_system_integrated = True
        self.memory_mesh_integrated = True
        
        # Registered clients (sandbox instances, Grace deployments, etc.)
        self.clients: Dict[str, Dict[str, Any]] = {}
        
        # Model updates from clients
        self.pending_updates: List[ModelUpdate] = []
        
        # Aggregated models per domain
        self.aggregated_models: Dict[str, AggregatedModel] = {}
        
        # Statistics
        self.stats = {
            "total_clients": 0,
            "total_updates_received": 0,
            "total_aggregations": 0,
            "domains_aggregated": set()
        }
        
        logger.info(f"[FEDERATED-LEARNING] Initialized federated learning system: {server_id}")
    
    # ==================== CLIENT MANAGEMENT ====================
    
    def register_client(
        self,
        client_id: str,
        client_type: FederatedClientType,
        domain: str,
        initial_capabilities: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a federated learning client (Grace-Aligned with Genesis Keys)."""
        try:
            # Create Genesis Key for client registration
            genesis_key_id = None
            genesis_key_id = None
            if self.genesis_service and self.session:
                try:
                    genesis_key = self.genesis_service.create_key(
                        key_type="SYSTEM_EVENT",
                        what_description=f"Federated learning client registered: {client_id}",
                        who_actor="federated_learning_system",
                        where_location=f"federated_server/{self.server_id}",
                        why_reason=f"Register client for {domain} domain federated learning",
                        how_method="client_registration",
                        context_data={
                            "client_id": client_id,
                            "client_type": client_type.value,
                            "domain": domain,
                            "server_id": self.server_id
                        },
                        tags=["federated_learning", "client_registration", domain],
                        session=self.session
                    )
                    genesis_key_id = genesis_key.key_id if genesis_key else None
                except Exception as e:
                    # Use try-except to ensure logger is available
                    try:
                        logger.warning(f"[FEDERATED-LEARNING] Genesis Key creation error: {e}")
                    except NameError:
                        # Fallback if logger not available
                        print(f"[FEDERATED-LEARNING] Genesis Key creation error: {e}")
            
            self.clients[client_id] = {
                "client_id": client_id,
                "client_type": client_type,
                "domain": domain,
                "registered_at": datetime.utcnow(),
                "last_update": None,
                "update_count": 0,
                "trust_score": 0.7,  # Initial trust
                "capabilities": initial_capabilities or {},
                "genesis_key_id": genesis_key_id  # Track with Genesis Key
            }
            
            self.stats["total_clients"] = len(self.clients)
            
            logger.info(
                f"[FEDERATED-LEARNING] Registered client: {client_id} "
                f"({client_type.value}, domain: {domain}, genesis_key: {genesis_key_id})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[FEDERATED-LEARNING] Client registration error: {e}")
            return False
    
    def unregister_client(self, client_id: str):
        """Unregister a federated learning client."""
        if client_id in self.clients:
            del self.clients[client_id]
            self.stats["total_clients"] = len(self.clients)
            logger.info(f"[FEDERATED-LEARNING] Unregistered client: {client_id}")
    
    # ==================== MODEL UPDATES ====================
    
    def submit_update(
        self,
        client_id: str,
        domain: str,
        patterns_learned: List[str],
        topics_learned: List[Dict[str, Any]],
        success_rate: float,
        files_processed: int,
        files_fixed: int
    ) -> str:
        """
        Submit a model update from a client.
        
        Privacy-preserving: Only shares learned patterns, not raw data.
        """
        try:
            if client_id not in self.clients:
                logger.warning(f"[FEDERATED-LEARNING] Unknown client: {client_id}")
                return None
            
            client = self.clients[client_id]
            client_type = client["client_type"]
            trust_score = client.get("trust_score", 0.7)
            
            # Create model update
            update_id = f"update_{hashlib.md5(f'{client_id}_{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
            
            # Create Genesis Key for model update (Grace-Aligned)
            update_genesis_key_id = None
            if self.genesis_service and self.session:
                try:
                    genesis_key = self.genesis_service.create_key(
                        key_type="LEARNING",
                        what_description=f"Federated learning model update from {client_id}",
                        who_actor=client_id,
                        where_location=f"federated_server/{self.server_id}",
                        why_reason=f"Submit learned patterns and topics for {domain} domain",
                        how_method="federated_learning_update",
                        input_data={
                            "patterns_count": len(patterns_learned),
                            "topics_count": len(topics_learned),
                            "success_rate": success_rate,
                            "files_processed": files_processed,
                            "files_fixed": files_fixed
                        },
                        output_data={
                            "update_id": update_id,
                            "trust_score": trust_score
                        },
                        context_data={
                            "client_id": client_id,
                            "domain": domain,
                            "patterns": patterns_learned[:5],  # Sample patterns
                            "topics": topics_learned[:3]  # Sample topics
                        },
                        tags=["federated_learning", "model_update", domain],
                        session=self.session
                    )
                    update_genesis_key_id = genesis_key.key_id if genesis_key else None
                except Exception as e:
                    # Use try-except to ensure logger is available
                    try:
                        logger.warning(f"[FEDERATED-LEARNING] Genesis Key creation error: {e}")
                    except NameError:
                        # Fallback if logger not available
                        print(f"[FEDERATED-LEARNING] Genesis Key creation error: {e}")
            
            # Extract model weights (patterns as "weights")
            model_weights = {
                "patterns": patterns_learned,
                "topics": topics_learned,
                "success_rate": success_rate,
                "files_processed": files_processed,
                "files_fixed": files_fixed
            }
            
            update = ModelUpdate(
                client_id=client_id,
                client_type=client_type,
                domain=domain,
                update_id=update_id,
                model_weights=model_weights,
                patterns_learned=patterns_learned,
                topics_learned=topics_learned,
                success_rate=success_rate,
                files_processed=files_processed,
                files_fixed=files_fixed,
                trust_score=trust_score
            )
            
            # Store Genesis Key ID in update metadata
            if update_genesis_key_id:
                update.model_weights["genesis_key_id"] = update_genesis_key_id
            
            # Add to pending updates
            self.pending_updates.append(update)
            
            # Update client stats
            client["last_update"] = datetime.utcnow()
            client["update_count"] += 1
            
            self.stats["total_updates_received"] += 1
            
            logger.info(
                f"[FEDERATED-LEARNING] Received update from {client_id}: "
                f"{len(patterns_learned)} patterns, {len(topics_learned)} topics, "
                f"success_rate={success_rate:.2%}"
            )
            
            return update_id
            
        except Exception as e:
            logger.error(f"[FEDERATED-LEARNING] Update submission error: {e}")
            return None
    
    # ==================== MODEL AGGREGATION ====================
    
    def aggregate_models(
        self,
        domain: Optional[str] = None,
        min_updates: int = 2
    ) -> Dict[str, AggregatedModel]:
        """
        Aggregate model updates from clients.
        
        Uses federated averaging:
        - Weight updates by trust scores
        - Aggregate patterns and topics
        - Combine success rates
        """
        try:
            # Filter updates by domain if specified
            if domain:
                updates = [u for u in self.pending_updates if u.domain == domain]
            else:
                updates = self.pending_updates.copy()
            
            if len(updates) < min_updates:
                logger.debug(
                    f"[FEDERATED-LEARNING] Not enough updates for aggregation: "
                    f"{len(updates)} < {min_updates}"
                )
                return {}
            
            # Group updates by domain
            updates_by_domain = defaultdict(list)
            for update in updates:
                updates_by_domain[update.domain].append(update)
            
            aggregated = {}
            
            for domain, domain_updates in updates_by_domain.items():
                if len(domain_updates) < min_updates:
                    continue
                
                # Aggregate patterns (weighted by trust)
                aggregated_patterns = []
                pattern_weights = defaultdict(float)
                
                for update in domain_updates:
                    weight = update.trust_score
                    for pattern in update.patterns_learned:
                        pattern_weights[pattern] += weight
                
                # Sort patterns by aggregated weight
                sorted_patterns = sorted(
                    pattern_weights.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                aggregated_patterns = [p[0] for p in sorted_patterns[:50]]  # Top 50 patterns
                
                # Aggregate topics (weighted by trust)
                aggregated_topics = []
                topic_weights = defaultdict(lambda: {"weight": 0.0, "data": None})
                
                for update in domain_updates:
                    weight = update.trust_score
                    for topic in update.topics_learned:
                        topic_key = topic.get("topic_name", "") or str(topic)
                        if topic_key not in topic_weights or topic_weights[topic_key]["weight"] < weight:
                            topic_weights[topic_key] = {"weight": weight, "data": topic}
                
                aggregated_topics = [
                    t["data"] for t in sorted(
                        topic_weights.values(),
                        key=lambda x: x["weight"],
                        reverse=True
                    )[:30]  # Top 30 topics
                ]
                
                # Aggregate success rate (weighted average)
                total_weight = sum(u.trust_score for u in domain_updates)
                if total_weight > 0:
                    avg_success_rate = sum(
                        u.success_rate * u.trust_score for u in domain_updates
                    ) / total_weight
                else:
                    avg_success_rate = sum(u.success_rate for u in domain_updates) / len(domain_updates)
                
                # Aggregate file counts
                total_files_processed = sum(u.files_processed for u in domain_updates)
                total_files_fixed = sum(u.files_fixed for u in domain_updates)
                
                # Create aggregated model
                existing_model = self.aggregated_models.get(domain)
                model_version = (existing_model.model_version + 1) if existing_model else 1
                
                aggregated_model = AggregatedModel(
                    domain=domain,
                    aggregated_patterns=aggregated_patterns,
                    aggregated_topics=aggregated_topics,
                    average_success_rate=avg_success_rate,
                    total_files_processed=total_files_processed,
                    total_files_fixed=total_files_fixed,
                    client_count=len(domain_updates),
                    last_updated=datetime.utcnow(),
                    model_version=model_version
                )
                
                self.aggregated_models[domain] = aggregated_model
                aggregated[domain] = aggregated_model
                
                self.stats["total_aggregations"] += 1
                self.stats["domains_aggregated"].add(domain)
                
                logger.info(
                    f"[FEDERATED-LEARNING] Aggregated model for {domain}: "
                    f"{len(aggregated_patterns)} patterns, {len(aggregated_topics)} topics, "
                    f"success_rate={avg_success_rate:.2%}, {len(domain_updates)} clients"
                )
                
                # Create Genesis Key for model aggregation (Grace-Aligned)
                aggregation_genesis_key_id = None
                if self.genesis_service and self.session:
                    try:
                        genesis_key = self.genesis_service.create_key(
                            key_type="LEARNING",
                            what_description=f"Federated learning model aggregation for {domain}",
                            who_actor="federated_learning_system",
                            where_location=f"federated_server/{self.server_id}",
                            why_reason=f"Aggregate learned patterns from {len(domain_updates)} clients for {domain} domain",
                            how_method="federated_aggregation",
                            input_data={
                                "client_count": len(domain_updates),
                                "updates_received": len(domain_updates),
                                "domain": domain
                            },
                            output_data={
                                "patterns_count": len(aggregated_patterns),
                                "topics_count": len(aggregated_topics),
                                "average_success_rate": avg_success_rate,
                                "model_version": model_version
                            },
                            context_data={
                                "domain": domain,
                                "clients": [u.client_id for u in domain_updates],
                                "aggregated_patterns_sample": aggregated_patterns[:5],
                                "aggregated_topics_sample": [t.get("topic_name", str(t)) for t in aggregated_topics[:3]]
                            },
                            tags=["federated_learning", "model_aggregation", domain],
                            session=self.session
                        )
                        aggregation_genesis_key_id = genesis_key.key_id if genesis_key else None
                    except Exception as e:
                        # Use try-except to ensure logger is available
                        try:
                            logger.warning(f"[FEDERATED-LEARNING] Genesis Key creation error: {e}")
                        except NameError:
                            # Fallback if logger not available
                            print(f"[FEDERATED-LEARNING] Genesis Key creation error: {e}")
                
                # Store Genesis Key ID in aggregated model
                if aggregation_genesis_key_id:
                    aggregated_model.aggregated_patterns.append(f"[Genesis:{aggregation_genesis_key_id}]")
                
                # Store aggregated model in learning memory for LLMs (Grace-Aligned)
                self._store_in_learning_memory(domain, aggregated_model, aggregation_genesis_key_id)
                
                # Apply Grace-Aligned enhancements for maximum learning
                self._apply_grace_aligned_enhancements(domain, aggregated_model, aggregation_genesis_key_id)
            
            # Clear processed updates
            self.pending_updates = []
            
            return aggregated
            
        except Exception as e:
            logger.error(f"[FEDERATED-LEARNING] Model aggregation error: {e}")
            return {}
    
    # ==================== MODEL DISTRIBUTION ====================
    
    def get_aggregated_model(self, domain: str) -> Optional[AggregatedModel]:
        """Get aggregated model for a domain."""
        return self.aggregated_models.get(domain)
    
    def get_all_models(self) -> Dict[str, AggregatedModel]:
        """Get all aggregated models."""
        return self.aggregated_models.copy()
    
    def distribute_model_to_client(
        self,
        client_id: str,
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """
        Distribute aggregated model to a client.
        
        Client can use this to improve its local model.
        """
        model = self.get_aggregated_model(domain)
        
        if not model:
            return None
        
        # Return model in format client can use
        return {
            "domain": domain,
            "patterns": model.aggregated_patterns,
            "topics": model.aggregated_topics,
            "average_success_rate": model.average_success_rate,
            "model_version": model.model_version,
            "last_updated": model.last_updated.isoformat()
        }
    
    # ==================== TRUST MANAGEMENT ====================
    
    def update_client_trust(
        self,
        client_id: str,
        new_trust_score: float
    ):
        """Update trust score for a client."""
        if client_id in self.clients:
            old_trust = self.clients[client_id]["trust_score"]
            self.clients[client_id]["trust_score"] = new_trust_score
            
            logger.info(
                f"[FEDERATED-LEARNING] Updated trust for {client_id}: "
                f"{old_trust:.2f} → {new_trust_score:.2f}"
            )
    
    def calculate_client_trust(
        self,
        client_id: str,
        update_quality: float,
        consistency_with_others: float
    ) -> float:
        """
        Calculate trust score for a client (Grace-Aligned Trust System).
        
        Uses Grace's trust scoring principles:
        - Source reliability
        - Outcome quality
        - Consistency with other clients
        - Validation history
        """
        if client_id not in self.clients:
            return 0.5
        
        client = self.clients[client_id]
        
        # Grace-Aligned Trust Calculation
        # Weighted by: outcome quality (60%), consistency (30%), source reliability (10%)
        source_reliability = 0.7  # Default for federated clients
        if client.get("update_count", 0) > 10:
            source_reliability = 0.8  # Higher reliability with more updates
        if client.get("update_count", 0) > 50:
            source_reliability = 0.9  # Very high reliability with many updates
        
        # Trust = weighted average (Grace-aligned)
        trust = (
            0.6 * update_quality +
            0.3 * consistency_with_others +
            0.1 * source_reliability
        )
        
        # Apply trust decay for stale clients (Grace-aligned)
        if client.get("last_update"):
            days_since_update = (datetime.utcnow() - client["last_update"]).days
            if days_since_update > 7:
                decay_factor = max(0.5, 1.0 - (days_since_update - 7) * 0.05)
                trust = trust * decay_factor
        
        # Update client trust
        self.update_client_trust(client_id, trust)
        
        # Create Genesis Key for trust update (Grace-Aligned)
        if self.genesis_service and self.session:
            try:
                self.genesis_service.create_key(
                    key_type="SYSTEM_EVENT",
                    what_description=f"Federated client trust updated: {client_id}",
                    who_actor="federated_learning_system",
                    where_location=f"federated_server/{self.server_id}",
                    why_reason=f"Update trust score based on update quality and consistency",
                    how_method="trust_calculation",
                    input_data={
                        "client_id": client_id,
                        "update_quality": update_quality,
                        "consistency": consistency_with_others
                    },
                    output_data={
                        "old_trust": client.get("trust_score", 0.7),
                        "new_trust": trust
                    },
                    context_data={
                        "client_id": client_id,
                        "domain": client.get("domain"),
                        "update_count": client.get("update_count", 0)
                    },
                    tags=["federated_learning", "trust_update"],
                    session=self.session
                )
            except Exception as e:
                # Use try-except to ensure logger is available
                try:
                    logger.debug(f"[FEDERATED-LEARNING] Trust Genesis Key error: {e}")
                except NameError:
                    # Silent fail for debug messages
                    pass
        
        return trust
    
    # ==================== STATISTICS ====================
    
    def _store_in_learning_memory(
        self,
        domain: str,
        aggregated_model: AggregatedModel,
        aggregation_genesis_key_id: Optional[str] = None
    ):
        """
        Store aggregated federated learning model in learning memory.
        
        This makes the knowledge accessible to:
        1. Learning memory system (logging)
        2. LLMs (via Grace-Aligned LLM)
        3. Memory Mesh (for retrieval)
        """
        try:
            # Store via learning memory manager
            if self.learning_memory:
                try:
                    # Store aggregated patterns in learning memory (Grace-Aligned with Genesis Keys)
                    if self.learning_memory:
                        try:
                            # Store aggregated patterns
                            for pattern in aggregated_model.aggregated_patterns[:20]:  # Top 20 patterns
                                # Skip Genesis Key patterns
                                if pattern.startswith("[Genesis:"):
                                    continue
                                
                                try:
                                    # Create Genesis Key for each pattern (Grace-Aligned)
                                    pattern_genesis_key_id = None
                                    if self.genesis_service and self.session:
                                        try:
                                            genesis_key = self.genesis_service.create_key(
                                                key_type="LEARNING",
                                                what_description=f"Federated learning pattern: {pattern[:100]}",
                                                who_actor="federated_learning_system",
                                                where_location=f"federated_server/{self.server_id}",
                                                why_reason=f"Store aggregated pattern for {domain} domain",
                                                how_method="federated_learning_storage",
                                                input_data={
                                                    "pattern": pattern,
                                                    "domain": domain,
                                                    "model_version": aggregated_model.model_version
                                                },
                                                output_data={
                                                    "pattern": pattern,
                                                    "trust_score": 0.8,
                                                    "client_count": aggregated_model.client_count
                                                },
                                                context_data={
                                                    "domain": domain,
                                                    "source": "federated_learning",
                                                    "aggregation_genesis_key_id": aggregation_genesis_key_id
                                                },
                                                tags=["federated_learning", "pattern", domain],
                                                session=self.session
                                            )
                                            pattern_genesis_key_id = genesis_key.key_id
                                        except Exception as e:
                                            # Use try-except to ensure logger is available
                                            try:
                                                logger.debug(f"[FEDERATED-LEARNING] Pattern Genesis Key error: {e}")
                                            except NameError:
                                                # Silent fail for debug messages
                                                pass
                                    
                                    self.learning_memory.ingest_learning_data(
                                        learning_type="federated_pattern",
                                        learning_data={
                                            "context": {
                                                "domain": domain,
                                                "source": "federated_learning",
                                                "pattern": pattern,
                                                "model_version": aggregated_model.model_version,
                                                "client_count": aggregated_model.client_count,
                                                "genesis_key_id": pattern_genesis_key_id
                                            },
                                            "expected": {
                                                "pattern": pattern,
                                                "domain": domain,
                                                "trust_score": 0.8,
                                                "client_count": aggregated_model.client_count
                                            },
                                            "actual": {
                                                "pattern": pattern,
                                                "success_rate": aggregated_model.average_success_rate
                                            }
                                        },
                                        source="federated_learning",
                                        genesis_key_id=pattern_genesis_key_id
                                    )
                                except Exception as e:
                                    # Use try-except to ensure logger is available
                                    try:
                                        logger.debug(f"[FEDERATED-LEARNING] Pattern storage error: {e}")
                                    except NameError:
                                        # Silent fail for debug messages
                                        pass
                            
                            # Store aggregated topics
                            for topic in aggregated_model.aggregated_topics[:15]:  # Top 15 topics
                                try:
                                    topic_data = topic if isinstance(topic, dict) else {"topic_name": str(topic), "topic": str(topic)}
                                    self.learning_memory.ingest_learning_data(
                                        learning_type="federated_topic",
                                        learning_data={
                                            "context": {
                                                "domain": domain,
                                                "source": "federated_learning",
                                                "topic": topic_data,
                                                "model_version": aggregated_model.model_version,
                                                "client_count": aggregated_model.client_count
                                            },
                                            "expected": {
                                                "topic": topic_data,
                                                "domain": domain,
                                                "trust_score": 0.8,
                                                "client_count": aggregated_model.client_count
                                            },
                                            "actual": {
                                                "topic": topic_data,
                                                "success_rate": aggregated_model.average_success_rate
                                            }
                                        },
                                        source="federated_learning"
                                    )
                                except Exception as e:
                                    # Use try-except to ensure logger is available
                                    try:
                                        logger.debug(f"[FEDERATED-LEARNING] Topic storage error: {e}")
                                    except NameError:
                                        # Silent fail for debug messages
                                        pass
                        except Exception as e:
                            # Use try-except to ensure logger is available
                            try:
                                logger.warning(f"[FEDERATED-LEARNING] Learning memory storage error: {e}")
                            except NameError:
                                # Fallback if logger not available
                                print(f"[FEDERATED-LEARNING] Learning memory storage error: {e}")
                    
                    logger.info(
                        f"[FEDERATED-LEARNING] Stored aggregated model for {domain} in learning memory: "
                        f"{len(aggregated_model.aggregated_patterns)} patterns, "
                        f"{len(aggregated_model.aggregated_topics)} topics"
                    )
                except Exception as e:
                    logger.warning(f"[FEDERATED-LEARNING] Learning memory storage error: {e}")
            
            # Store via LLM orchestrator (Grace-Aligned LLM)
            if self.llm_orchestrator and hasattr(self.llm_orchestrator, "grace_aligned_llm"):
                try:
                    # Contribute aggregated patterns to Grace's learning
                    aggregated_knowledge = (
                        f"Federated learning aggregated {len(aggregated_model.aggregated_patterns)} patterns "
                        f"and {len(aggregated_model.aggregated_topics)} topics for {domain} domain. "
                        f"Success rate: {aggregated_model.average_success_rate:.2%}. "
                        f"Learned from {aggregated_model.client_count} clients."
                    )
                    
                    learning_id = self.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                        llm_output=aggregated_knowledge,
                        query=f"Federated learning aggregated model for {domain}",
                        trust_score=0.85,  # High trust for aggregated knowledge
                        genesis_key_id=aggregation_genesis_key_id,  # Grace-Aligned: Use Genesis Key
                        context={
                            "domain": domain,
                            "source": "federated_learning",
                            "model_version": aggregated_model.model_version,
                            "client_count": aggregated_model.client_count,
                            "patterns_count": len(aggregated_model.aggregated_patterns),
                            "topics_count": len(aggregated_model.aggregated_topics),
                            "average_success_rate": aggregated_model.average_success_rate,
                            "genesis_key_id": aggregation_genesis_key_id  # Grace-Aligned
                        }
                    )
                    
                    # Store individual patterns for LLM retrieval (Grace-Aligned with Genesis Keys)
                    for pattern in aggregated_model.aggregated_patterns[:30]:  # Top 30 patterns
                        # Skip Genesis Key patterns
                        if pattern.startswith("[Genesis:"):
                            continue
                        
                        try:
                            # Create Genesis Key for pattern contribution
                            pattern_genesis_key_id = None
                            if self.genesis_service and self.session:
                                try:
                                    genesis_key = self.genesis_service.create_key(
                                        key_type="LEARNING",
                                        what_description=f"Federated pattern contribution: {pattern[:100]}",
                                        who_actor="federated_learning_system",
                                        where_location=f"federated_server/{self.server_id}",
                                        why_reason=f"Contribute aggregated pattern to Grace-Aligned LLM for {domain}",
                                        how_method="federated_learning_llm_contribution",
                                        input_data={"pattern": pattern, "domain": domain},
                                        output_data={"pattern": pattern, "trust_score": 0.8},
                                        context_data={
                                            "domain": domain,
                                            "source": "federated_learning",
                                            "model_version": aggregated_model.model_version,
                                            "aggregation_genesis_key_id": aggregation_genesis_key_id
                                        },
                                        tags=["federated_learning", "llm_contribution", domain],
                                        session=self.session
                                    )
                                    pattern_genesis_key_id = genesis_key.key_id
                                except Exception as e:
                                    logger.debug(f"[FEDERATED-LEARNING] Pattern Genesis Key error: {e}")
                            
                            pattern_knowledge = f"[Federated-{domain}] {pattern}"
                            self.llm_orchestrator.grace_aligned_llm.contribute_to_grace_learning(
                                llm_output=pattern_knowledge,
                                query=f"{domain} fix pattern (federated)",
                                trust_score=0.8,
                                genesis_key_id=pattern_genesis_key_id,  # Grace-Aligned: Use Genesis Key
                                context={
                                    "domain": domain,
                                    "source": "federated_learning",
                                    "pattern": pattern,
                                    "model_version": aggregated_model.model_version,
                                    "genesis_key_id": pattern_genesis_key_id  # Grace-Aligned
                                }
                            )
                        except Exception as e:
                            # Use try-except to ensure logger is available
                            try:
                                logger.debug(f"[FEDERATED-LEARNING] Pattern contribution error: {e}")
                            except NameError:
                                # Silent fail for debug messages
                                pass
                    
                    logger.info(
                        f"[FEDERATED-LEARNING] Contributed aggregated model for {domain} to Grace-Aligned LLM: "
                        f"learning_id={learning_id}"
                    )
                except Exception as e:
                    # Use try-except to ensure logger is available
                    try:
                        logger.warning(f"[FEDERATED-LEARNING] LLM orchestrator storage error: {e}")
                    except NameError:
                        # Fallback if logger not available
                        print(f"[FEDERATED-LEARNING] LLM orchestrator storage error: {e}")
            
        except Exception as e:
            # Use try-except to ensure logger is available
            try:
                logger.error(f"[FEDERATED-LEARNING] Learning memory storage error: {e}")
            except NameError:
                # Fallback if logger not available
                print(f"[FEDERATED-LEARNING] Learning memory storage error: {e}")
    
    def _apply_grace_aligned_enhancements(
        self,
        domain: str,
        aggregated_model: AggregatedModel,
        aggregation_genesis_key_id: Optional[str]
    ):
        """Apply Grace-Aligned enhancements to push learning as far as possible."""
        try:
            # Try to get Grace-Aligned Federated Learning enhancements
            try:
                from cognitive.grace_aligned_federated_learning import get_grace_aligned_federated_learning
                
                grace_aligned_fl = get_grace_aligned_federated_learning(
                    federated_server=self,
                    genesis_service=self.genesis_service,
                    memory_mesh_integration=None,  # Would get from learning_memory if available
                    trust_system=None,
                    ooda_loop=None
                )
                
                # Enforce OODA invariants
                all_passed, violations = grace_aligned_fl.enforce_ooda_invariants(
                    aggregated_model, domain
                )
                
                if not all_passed:
                    logger.warning(
                        f"[FEDERATED-LEARNING] Invariant violations for {domain}: {violations}"
                    )
                
                # Optimize learning (cross-domain synthesis, pattern mining, etc.)
                optimized = grace_aligned_fl.optimize_learning({domain: aggregated_model})
                
                if optimized and domain in optimized:
                    optimized_model = optimized[domain]
                    logger.info(
                        f"[FEDERATED-LEARNING] Optimized model for {domain}: "
                        f"{optimized_model.get('cross_domain_synthesis', 0)} cross-domain patterns, "
                        f"{optimized_model.get('refined_patterns', 0)} refined patterns"
                    )
                
                # Deep Memory Mesh integration
                grace_aligned_fl.integrate_with_memory_mesh(aggregated_model, domain)
                
            except Exception as e:
                # Use try-except to ensure logger is available
                try:
                    logger.debug(f"[FEDERATED-LEARNING] Grace-Aligned enhancements not available: {e}")
                except NameError:
                    # Silent fail for debug messages
                    pass
                
        except Exception as e:
            # Use try-except to ensure logger is available
            try:
                logger.warning(f"[FEDERATED-LEARNING] Grace-Aligned enhancement error: {e}")
            except NameError:
                # Fallback if logger not available
                print(f"[FEDERATED-LEARNING] Grace-Aligned enhancement error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get federated learning statistics."""
        return {
            "stats": self.stats.copy(),
            "clients": {
                client_id: {
                    "type": client["client_type"].value,
                    "domain": client["domain"],
                    "update_count": client["update_count"],
                    "trust_score": client["trust_score"],
                    "last_update": client["last_update"].isoformat() if client["last_update"] else None
                }
                for client_id, client in self.clients.items()
            },
            "aggregated_models": {
                domain: {
                    "patterns_count": len(model.aggregated_patterns),
                    "topics_count": len(model.aggregated_topics),
                    "average_success_rate": model.average_success_rate,
                    "client_count": model.client_count,
                    "model_version": model.model_version
                }
                for domain, model in self.aggregated_models.items()
            }
        }


def get_federated_learning_system(
    server_id: str = "grace_federated_server",
    enable_cross_deployment: bool = False,
    learning_memory_manager=None,
    llm_orchestrator=None,
    genesis_service=None,
    session=None
) -> FederatedLearningSystem:
    """Factory function to get Federated Learning System (Grace-Aligned)."""
    return FederatedLearningSystem(
        server_id=server_id,
        enable_cross_deployment=enable_cross_deployment,
        learning_memory_manager=learning_memory_manager,
        llm_orchestrator=llm_orchestrator,
        genesis_service=genesis_service,
        session=session
    )
