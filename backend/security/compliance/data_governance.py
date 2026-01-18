"""
GRACE Data Governance

Provides data governance capabilities for compliance:
- Data classification
- Data lineage tracking
- Retention policies
- Right to erasure (GDPR)
- Data access governance
"""

import hashlib
import json
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class DataClassification(str, Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class DataCategory(str, Enum):
    """Categories of data for classification."""
    PII = "pii"  # Personally Identifiable Information
    PHI = "phi"  # Protected Health Information
    PCI = "pci"  # Payment Card Industry
    FINANCIAL = "financial"
    CREDENTIALS = "credentials"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    BUSINESS_CONFIDENTIAL = "business_confidential"
    SYSTEM = "system"
    GENERAL = "general"


@dataclass
class ClassificationRule:
    """Rule for automatic data classification."""
    rule_id: str
    name: str
    pattern: str  # Regex pattern
    data_category: DataCategory
    classification: DataClassification
    priority: int = 0
    
    def matches(self, content: str) -> bool:
        """Check if content matches this rule."""
        try:
            return bool(re.search(self.pattern, content, re.IGNORECASE))
        except re.error:
            return False


@dataclass
class DataAsset:
    """A data asset with classification."""
    asset_id: str
    name: str
    location: str  # Table, file path, API endpoint
    classification: DataClassification
    categories: List[DataCategory]
    owner: str
    created_at: datetime
    last_accessed: Optional[datetime] = None
    retention_days: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "location": self.location,
            "classification": self.classification.value,
            "categories": [c.value for c in self.categories],
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "retention_days": self.retention_days,
        }


@dataclass 
class LineageNode:
    """A node in the data lineage graph."""
    node_id: str
    asset_id: str
    operation: str  # "source", "transform", "destination"
    timestamp: datetime
    actor: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageEdge:
    """An edge in the data lineage graph."""
    source_id: str
    target_id: str
    transformation: str
    timestamp: datetime


class ClassificationPolicy:
    """
    Automatic data classification policy.
    
    Uses pattern matching to classify data.
    """
    
    def __init__(self):
        self._rules: List[ClassificationRule] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Set up default classification rules."""
        rules = [
            # PII patterns
            ClassificationRule(
                rule_id="email",
                name="Email Address",
                pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                data_category=DataCategory.PII,
                classification=DataClassification.CONFIDENTIAL,
                priority=10,
            ),
            ClassificationRule(
                rule_id="ssn",
                name="Social Security Number",
                pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                data_category=DataCategory.PII,
                classification=DataClassification.RESTRICTED,
                priority=100,
            ),
            ClassificationRule(
                rule_id="phone",
                name="Phone Number",
                pattern=r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                data_category=DataCategory.PII,
                classification=DataClassification.CONFIDENTIAL,
                priority=5,
            ),
            # PCI patterns
            ClassificationRule(
                rule_id="credit_card",
                name="Credit Card Number",
                pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
                data_category=DataCategory.PCI,
                classification=DataClassification.RESTRICTED,
                priority=100,
            ),
            # Credential patterns
            ClassificationRule(
                rule_id="api_key",
                name="API Key Pattern",
                pattern=r"\b[A-Za-z0-9_-]{32,64}\b",
                data_category=DataCategory.CREDENTIALS,
                classification=DataClassification.TOP_SECRET,
                priority=50,
            ),
            ClassificationRule(
                rule_id="password_field",
                name="Password Field",
                pattern=r"(password|passwd|secret|api_key|token)[\"']?\s*[:=]",
                data_category=DataCategory.CREDENTIALS,
                classification=DataClassification.TOP_SECRET,
                priority=80,
            ),
            # PHI patterns
            ClassificationRule(
                rule_id="medical_record",
                name="Medical Record Number",
                pattern=r"\bMRN[:\s]*\d{6,10}\b",
                data_category=DataCategory.PHI,
                classification=DataClassification.RESTRICTED,
                priority=90,
            ),
        ]
        
        self._rules = sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def classify(self, content: str) -> Dict[str, Any]:
        """
        Classify content based on rules.
        
        Returns highest classification and all matching categories.
        """
        matches: List[ClassificationRule] = []
        
        for rule in self._rules:
            if rule.matches(content):
                matches.append(rule)
        
        if not matches:
            return {
                "classification": DataClassification.PUBLIC,
                "categories": [DataCategory.GENERAL],
                "matched_rules": [],
            }
        
        # Get highest classification
        classification_order = [
            DataClassification.PUBLIC,
            DataClassification.INTERNAL,
            DataClassification.CONFIDENTIAL,
            DataClassification.RESTRICTED,
            DataClassification.TOP_SECRET,
        ]
        
        highest = max(matches, key=lambda r: classification_order.index(r.classification))
        categories = list(set(r.data_category for r in matches))
        
        return {
            "classification": highest.classification,
            "categories": categories,
            "matched_rules": [r.rule_id for r in matches],
        }
    
    def add_rule(self, rule: ClassificationRule):
        """Add a classification rule."""
        self._rules.append(rule)
        self._rules = sorted(self._rules, key=lambda r: r.priority, reverse=True)


class DataLineage:
    """
    Tracks data lineage through the system.
    
    Records data flow from source to destination.
    """
    
    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []
        self._lock = threading.RLock()
    
    def record_source(
        self,
        asset_id: str,
        actor: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a data source."""
        node_id = f"LN-{uuid.uuid4().hex[:8]}"
        
        node = LineageNode(
            node_id=node_id,
            asset_id=asset_id,
            operation="source",
            timestamp=datetime.utcnow(),
            actor=actor,
            metadata=metadata or {},
        )
        
        with self._lock:
            self._nodes[node_id] = node
        
        return node_id
    
    def record_transform(
        self,
        source_node_id: str,
        asset_id: str,
        transformation: str,
        actor: str,
    ) -> str:
        """Record a data transformation."""
        node_id = f"LN-{uuid.uuid4().hex[:8]}"
        
        node = LineageNode(
            node_id=node_id,
            asset_id=asset_id,
            operation="transform",
            timestamp=datetime.utcnow(),
            actor=actor,
            metadata={"transformation": transformation},
        )
        
        edge = LineageEdge(
            source_id=source_node_id,
            target_id=node_id,
            transformation=transformation,
            timestamp=datetime.utcnow(),
        )
        
        with self._lock:
            self._nodes[node_id] = node
            self._edges.append(edge)
        
        return node_id
    
    def record_destination(
        self,
        source_node_id: str,
        asset_id: str,
        actor: str,
    ) -> str:
        """Record data arriving at destination."""
        node_id = f"LN-{uuid.uuid4().hex[:8]}"
        
        node = LineageNode(
            node_id=node_id,
            asset_id=asset_id,
            operation="destination",
            timestamp=datetime.utcnow(),
            actor=actor,
        )
        
        edge = LineageEdge(
            source_id=source_node_id,
            target_id=node_id,
            transformation="destination",
            timestamp=datetime.utcnow(),
        )
        
        with self._lock:
            self._nodes[node_id] = node
            self._edges.append(edge)
        
        return node_id
    
    def get_lineage(self, asset_id: str) -> Dict[str, Any]:
        """Get full lineage for an asset."""
        with self._lock:
            # Find all nodes for this asset
            asset_nodes = [n for n in self._nodes.values() if n.asset_id == asset_id]
            
            # Find all connected edges
            node_ids = {n.node_id for n in asset_nodes}
            relevant_edges = []
            
            # Trace upstream
            to_check = set(node_ids)
            while to_check:
                current = to_check.pop()
                for edge in self._edges:
                    if edge.target_id == current:
                        relevant_edges.append(edge)
                        if edge.source_id not in node_ids:
                            node_ids.add(edge.source_id)
                            to_check.add(edge.source_id)
            
            # Trace downstream
            to_check = set(node_ids)
            checked = set()
            while to_check:
                current = to_check.pop()
                if current in checked:
                    continue
                checked.add(current)
                
                for edge in self._edges:
                    if edge.source_id == current:
                        relevant_edges.append(edge)
                        if edge.target_id not in node_ids:
                            node_ids.add(edge.target_id)
                            to_check.add(edge.target_id)
            
            nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]
            
            return {
                "asset_id": asset_id,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "asset_id": n.asset_id,
                        "operation": n.operation,
                        "timestamp": n.timestamp.isoformat(),
                        "actor": n.actor,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "source": e.source_id,
                        "target": e.target_id,
                        "transformation": e.transformation,
                    }
                    for e in relevant_edges
                ],
            }


class RetentionSchedule:
    """
    Manages data retention schedules.
    """
    
    DEFAULT_RETENTION = {
        DataClassification.PUBLIC: timedelta(days=365),
        DataClassification.INTERNAL: timedelta(days=365 * 3),
        DataClassification.CONFIDENTIAL: timedelta(days=365 * 5),
        DataClassification.RESTRICTED: timedelta(days=365 * 7),
        DataClassification.TOP_SECRET: timedelta(days=365 * 10),
    }
    
    def __init__(self):
        self._custom_retention: Dict[str, timedelta] = {}
    
    def get_retention(
        self,
        classification: DataClassification,
        asset_id: Optional[str] = None,
    ) -> timedelta:
        """Get retention period for classification/asset."""
        if asset_id and asset_id in self._custom_retention:
            return self._custom_retention[asset_id]
        return self.DEFAULT_RETENTION.get(classification, timedelta(days=365))
    
    def set_custom_retention(self, asset_id: str, retention: timedelta):
        """Set custom retention for an asset."""
        self._custom_retention[asset_id] = retention


@dataclass
class ErasureRequest:
    """Request for data erasure (GDPR Article 17)."""
    request_id: str
    subject_id: str  # Data subject identifier
    requested_at: datetime
    requested_by: str
    reason: str
    status: str = "pending"  # pending, in_progress, completed, rejected
    assets_to_erase: List[str] = field(default_factory=list)
    erasure_proof: Dict[str, Any] = field(default_factory=dict)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "subject_id": self.subject_id,
            "requested_at": self.requested_at.isoformat(),
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class RightToErasure:
    """
    Implements GDPR Right to Erasure (Article 17).
    
    Handles deletion requests with full audit trail.
    """
    
    def __init__(self):
        self._requests: Dict[str, ErasureRequest] = {}
        self._erasure_handlers: List[Callable[[str, List[str]], Dict[str, bool]]] = []
        self._lock = threading.RLock()
    
    def register_handler(
        self,
        handler: Callable[[str, List[str]], Dict[str, bool]],
    ):
        """Register an erasure handler."""
        self._erasure_handlers.append(handler)
    
    def create_request(
        self,
        subject_id: str,
        requested_by: str,
        reason: str,
        assets: Optional[List[str]] = None,
    ) -> ErasureRequest:
        """Create an erasure request."""
        request = ErasureRequest(
            request_id=f"ER-{uuid.uuid4().hex[:8]}",
            subject_id=subject_id,
            requested_at=datetime.utcnow(),
            requested_by=requested_by,
            reason=reason,
            assets_to_erase=assets or [],
        )
        
        with self._lock:
            self._requests[request.request_id] = request
        
        self._audit_request(request, "created")
        logger.info(f"[ERASURE] Request created: {request.request_id}")
        
        return request
    
    def process_request(self, request_id: str) -> Dict[str, Any]:
        """Process an erasure request."""
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                return {"error": "Request not found"}
            
            if request.status != "pending":
                return {"error": f"Request already {request.status}"}
            
            request.status = "in_progress"
        
        results = {}
        
        for handler in self._erasure_handlers:
            try:
                handler_results = handler(request.subject_id, request.assets_to_erase)
                results.update(handler_results)
            except Exception as e:
                logger.error(f"[ERASURE] Handler failed: {e}")
                results["handler_error"] = str(e)
        
        with self._lock:
            request.status = "completed"
            request.completed_at = datetime.utcnow()
            request.erasure_proof = {
                "results": results,
                "processed_at": request.completed_at.isoformat(),
                "proof_hash": hashlib.sha256(
                    json.dumps(results, sort_keys=True).encode()
                ).hexdigest(),
            }
        
        self._audit_request(request, "completed")
        logger.info(f"[ERASURE] Request completed: {request_id}")
        
        return {
            "request_id": request_id,
            "status": "completed",
            "results": results,
        }
    
    def get_request(self, request_id: str) -> Optional[ErasureRequest]:
        """Get an erasure request."""
        return self._requests.get(request_id)
    
    def _audit_request(self, request: ErasureRequest, action: str):
        """Audit an erasure request."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.DATA_DELETION,
                    action_description=f"Erasure request {action}: {request.request_id}",
                    actor_type="data_governance",
                    actor_id="right_to_erasure",
                    severity="info",
                    component="compliance.data_governance",
                    context=request.to_dict(),
                )
        except Exception as e:
            logger.debug(f"[ERASURE] Audit failed: {e}")


# Singletons
_classification_policy: Optional[ClassificationPolicy] = None
_data_lineage: Optional[DataLineage] = None
_right_to_erasure: Optional[RightToErasure] = None


def get_classification_policy() -> ClassificationPolicy:
    """Get classification policy singleton."""
    global _classification_policy
    if _classification_policy is None:
        _classification_policy = ClassificationPolicy()
    return _classification_policy


def get_data_lineage() -> DataLineage:
    """Get data lineage singleton."""
    global _data_lineage
    if _data_lineage is None:
        _data_lineage = DataLineage()
    return _data_lineage


def get_right_to_erasure() -> RightToErasure:
    """Get right to erasure singleton."""
    global _right_to_erasure
    if _right_to_erasure is None:
        _right_to_erasure = RightToErasure()
    return _right_to_erasure
