"""
Data Integrity for GRACE

Provides integrity verification:
- Merkle tree for batch verification
- Content-addressable storage hashing
- Tamper detection
- Integration with immutable audit
"""

import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from .hashing import hash_sha256, ContentHasher, HashAlgorithm

logger = logging.getLogger(__name__)


@dataclass
class MerkleNode:
    """Node in a Merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    data: Optional[bytes] = None
    index: Optional[int] = None
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return self.left is None and self.right is None


@dataclass
class MerkleProof:
    """Merkle proof for a single item."""
    leaf_hash: str
    leaf_index: int
    proof_hashes: List[Tuple[str, str]]
    root_hash: str
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "leaf_hash": self.leaf_hash,
            "leaf_index": self.leaf_index,
            "proof_hashes": self.proof_hashes,
            "root_hash": self.root_hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MerkleProof':
        """Deserialize from dictionary."""
        return cls(
            leaf_hash=data["leaf_hash"],
            leaf_index=data["leaf_index"],
            proof_hashes=data["proof_hashes"],
            root_hash=data["root_hash"],
        )


class MerkleTree:
    """Merkle tree for batch integrity verification."""
    
    def __init__(self, items: Optional[List[bytes]] = None):
        self._leaves: List[MerkleNode] = []
        self._root: Optional[MerkleNode] = None
        if items:
            self.build(items)
    
    def build(self, items: List[bytes]) -> str:
        """Build the Merkle tree from a list of items."""
        if not items:
            self._root = MerkleNode(hash=hash_sha256(b""))
            return self._root.hash
        
        self._leaves = [
            MerkleNode(
                hash=hash_sha256(item),
                data=item,
                index=i
            )
            for i, item in enumerate(items)
        ]
        
        if len(self._leaves) % 2 == 1:
            self._leaves.append(MerkleNode(
                hash=self._leaves[-1].hash,
                data=self._leaves[-1].data,
                index=len(self._leaves),
            ))
        
        self._root = self._build_tree(self._leaves)
        return self._root.hash
    
    def _build_tree(self, nodes: List[MerkleNode]) -> MerkleNode:
        """Recursively build tree from nodes."""
        if len(nodes) == 1:
            return nodes[0]
        
        parent_nodes = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            combined = left.hash + right.hash
            parent_hash = hash_sha256(combined)
            parent_nodes.append(MerkleNode(
                hash=parent_hash,
                left=left,
                right=right,
            ))
        
        if len(parent_nodes) % 2 == 1 and len(parent_nodes) > 1:
            parent_nodes.append(MerkleNode(
                hash=parent_nodes[-1].hash,
                left=parent_nodes[-1].left,
                right=parent_nodes[-1].right,
            ))
        
        return self._build_tree(parent_nodes)
    
    @property
    def root_hash(self) -> str:
        """Get the root hash of the tree."""
        return self._root.hash if self._root else ""
    
    def get_proof(self, index: int) -> Optional[MerkleProof]:
        """Get a proof for the item at the given index."""
        if not self._leaves or index >= len(self._leaves):
            return None
        
        proof_hashes = []
        nodes = self._leaves.copy()
        current_index = index
        
        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])
            
            if current_index % 2 == 0:
                sibling_index = current_index + 1
                position = "right"
            else:
                sibling_index = current_index - 1
                position = "left"
            
            if sibling_index < len(nodes):
                proof_hashes.append((position, nodes[sibling_index].hash))
            
            new_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                combined = left.hash + right.hash
                new_nodes.append(MerkleNode(hash=hash_sha256(combined)))
            
            nodes = new_nodes
            current_index = current_index // 2
        
        return MerkleProof(
            leaf_hash=self._leaves[index].hash,
            leaf_index=index,
            proof_hashes=proof_hashes,
            root_hash=self.root_hash,
        )
    
    @staticmethod
    def verify_proof(proof: MerkleProof, item: bytes) -> bool:
        """Verify a Merkle proof."""
        current_hash = hash_sha256(item)
        
        if current_hash != proof.leaf_hash:
            return False
        
        for position, sibling_hash in proof.proof_hashes:
            if position == "right":
                combined = current_hash + sibling_hash
            else:
                combined = sibling_hash + current_hash
            current_hash = hash_sha256(combined)
        
        return current_hash == proof.root_hash
    
    def add_item(self, item: bytes) -> str:
        """Add an item and rebuild the tree."""
        all_items = [leaf.data for leaf in self._leaves if leaf.data]
        all_items.append(item)
        return self.build(all_items)


class ContentAddressableStorage:
    """Content-addressable storage with integrity verification."""
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        self._storage: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self.hasher = ContentHasher(algorithm)
    
    def store(self, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store content and return its hash as the address."""
        content_hash = self.hasher.hash(content)
        self._storage[content_hash] = content
        self._metadata[content_hash] = {
            "size": len(content),
            "stored_at": datetime.utcnow().isoformat(),
            "algorithm": self.hasher.algorithm.value,
            **(metadata or {}),
        }
        return content_hash
    
    def retrieve(self, content_hash: str) -> Optional[bytes]:
        """Retrieve content by its hash."""
        return self._storage.get(content_hash)
    
    def verify(self, content_hash: str) -> bool:
        """Verify stored content hasn't been tampered with."""
        content = self._storage.get(content_hash)
        if content is None:
            return False
        computed_hash = self.hasher.hash(content)
        return computed_hash == content_hash
    
    def exists(self, content_hash: str) -> bool:
        """Check if content exists."""
        return content_hash in self._storage
    
    def get_metadata(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get metadata for stored content."""
        return self._metadata.get(content_hash)
    
    def delete(self, content_hash: str) -> bool:
        """Delete content (returns False if not found)."""
        if content_hash in self._storage:
            del self._storage[content_hash]
            del self._metadata[content_hash]
            return True
        return False
    
    def list_all(self) -> List[str]:
        """List all content hashes."""
        return list(self._storage.keys())
    
    def verify_all(self) -> Dict[str, bool]:
        """Verify integrity of all stored content."""
        return {
            content_hash: self.verify(content_hash)
            for content_hash in self._storage.keys()
        }


@dataclass
class TamperEvent:
    """Record of a detected tampering attempt."""
    resource_id: str
    resource_type: str
    detected_at: datetime
    expected_hash: str
    actual_hash: str
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)


class TamperDetector:
    """Detect tampering in data and files."""
    
    def __init__(self):
        self._checksums: Dict[str, str] = {}
        self._audit_callback = None
        self._events: List[TamperEvent] = []
    
    def set_audit_callback(self, callback):
        """Set callback for audit logging."""
        self._audit_callback = callback
    
    def _audit(self, event: TamperEvent):
        """Log a tamper event."""
        self._events.append(event)
        if self._audit_callback:
            self._audit_callback({
                "event_type": "TAMPER_DETECTED",
                "resource_id": event.resource_id,
                "resource_type": event.resource_type,
                "detected_at": event.detected_at.isoformat(),
                "expected_hash": event.expected_hash,
                "actual_hash": event.actual_hash,
                "severity": event.severity,
                "details": event.details,
            })
    
    def register(self, resource_id: str, content: bytes) -> str:
        """Register content for tamper detection."""
        checksum = hash_sha256(content)
        self._checksums[resource_id] = checksum
        return checksum
    
    def verify(self, resource_id: str, content: bytes) -> Tuple[bool, Optional[TamperEvent]]:
        """Verify content hasn't been tampered with."""
        expected = self._checksums.get(resource_id)
        if expected is None:
            return True, None
        
        actual = hash_sha256(content)
        if actual == expected:
            return True, None
        
        event = TamperEvent(
            resource_id=resource_id,
            resource_type="content",
            detected_at=datetime.utcnow(),
            expected_hash=expected,
            actual_hash=actual,
            severity="critical",
        )
        self._audit(event)
        return False, event
    
    def verify_file(self, resource_id: str, filepath: str) -> Tuple[bool, Optional[TamperEvent]]:
        """Verify a file hasn't been tampered with."""
        expected = self._checksums.get(resource_id)
        if expected is None:
            return True, None
        
        hasher = ContentHasher(HashAlgorithm.SHA256)
        actual = hasher.hash_file(filepath)
        
        if actual == expected:
            return True, None
        
        event = TamperEvent(
            resource_id=resource_id,
            resource_type="file",
            detected_at=datetime.utcnow(),
            expected_hash=expected,
            actual_hash=actual,
            severity="critical",
            details={"filepath": filepath},
        )
        self._audit(event)
        return False, event
    
    def get_events(self) -> List[TamperEvent]:
        """Get all detected tamper events."""
        return self._events.copy()
    
    def clear_events(self):
        """Clear tamper event history."""
        self._events.clear()


@dataclass
class AuditEntry:
    """Immutable audit log entry."""
    entry_id: str
    timestamp: datetime
    action: str
    actor: str
    resource: str
    data: Dict[str, Any]
    hash: str
    previous_hash: str
    signature: Optional[str] = None


class ImmutableAuditIntegration:
    """Integration with immutable audit logging."""
    
    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._last_hash: str = hash_sha256(b"genesis")
        self._entry_counter: int = 0
    
    def append(
        self,
        action: str,
        actor: str,
        resource: str,
        data: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> AuditEntry:
        """Append an entry to the audit log."""
        self._entry_counter += 1
        timestamp = datetime.utcnow()
        
        entry_data = {
            "entry_id": str(self._entry_counter),
            "timestamp": timestamp.isoformat(),
            "action": action,
            "actor": actor,
            "resource": resource,
            "data": data,
            "previous_hash": self._last_hash,
        }
        
        entry_hash = hash_sha256(json.dumps(entry_data, sort_keys=True, default=str))
        
        entry = AuditEntry(
            entry_id=str(self._entry_counter),
            timestamp=timestamp,
            action=action,
            actor=actor,
            resource=resource,
            data=data,
            hash=entry_hash,
            previous_hash=self._last_hash,
            signature=signature,
        )
        
        self._entries.append(entry)
        self._last_hash = entry_hash
        
        return entry
    
    def verify_chain(self) -> Tuple[bool, Optional[int]]:
        """Verify the integrity of the entire audit chain."""
        if not self._entries:
            return True, None
        
        expected_previous = hash_sha256(b"genesis")
        
        for i, entry in enumerate(self._entries):
            if entry.previous_hash != expected_previous:
                return False, i
            
            entry_data = {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action,
                "actor": entry.actor,
                "resource": entry.resource,
                "data": entry.data,
                "previous_hash": entry.previous_hash,
            }
            computed_hash = hash_sha256(json.dumps(entry_data, sort_keys=True, default=str))
            
            if computed_hash != entry.hash:
                return False, i
            
            expected_previous = entry.hash
        
        return True, None
    
    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get an entry by ID."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def get_entries_by_actor(self, actor: str) -> List[AuditEntry]:
        """Get all entries by a specific actor."""
        return [e for e in self._entries if e.actor == actor]
    
    def get_entries_by_resource(self, resource: str) -> List[AuditEntry]:
        """Get all entries for a specific resource."""
        return [e for e in self._entries if e.resource == resource]
    
    def get_entries_by_action(self, action: str) -> List[AuditEntry]:
        """Get all entries for a specific action."""
        return [e for e in self._entries if e.action == action]
    
    def export_chain(self) -> List[Dict[str, Any]]:
        """Export the entire chain as a list of dictionaries."""
        return [
            {
                "entry_id": e.entry_id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "actor": e.actor,
                "resource": e.resource,
                "data": e.data,
                "hash": e.hash,
                "previous_hash": e.previous_hash,
                "signature": e.signature,
            }
            for e in self._entries
        ]
    
    def import_chain(self, entries: List[Dict[str, Any]]) -> bool:
        """Import a chain and verify its integrity."""
        imported = []
        for data in entries:
            entry = AuditEntry(
                entry_id=data["entry_id"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                action=data["action"],
                actor=data["actor"],
                resource=data["resource"],
                data=data["data"],
                hash=data["hash"],
                previous_hash=data["previous_hash"],
                signature=data.get("signature"),
            )
            imported.append(entry)
        
        old_entries = self._entries
        old_last_hash = self._last_hash
        
        self._entries = imported
        if imported:
            self._last_hash = imported[-1].hash
            self._entry_counter = int(imported[-1].entry_id)
        
        valid, _ = self.verify_chain()
        if not valid:
            self._entries = old_entries
            self._last_hash = old_last_hash
            return False
        
        return True


def create_merkle_tree(items: List[bytes]) -> Tuple[str, MerkleTree]:
    """Convenience function: Create a Merkle tree."""
    tree = MerkleTree(items)
    return tree.root_hash, tree


def verify_merkle_proof(proof: MerkleProof, item: bytes) -> bool:
    """Convenience function: Verify a Merkle proof."""
    return MerkleTree.verify_proof(proof, item)


def detect_tampering(expected_hash: str, content: bytes) -> bool:
    """Convenience function: Check if content was tampered."""
    actual = hash_sha256(content)
    return actual != expected_hash
