"""
Deterministic Primitives for GRACE Cognitive Systems.

This module provides core utilities for deterministic operations:
- LogicalClock: Monotonic tick counter with persistence
- Canonicalizer: Stable serialization and hashing
- DeterministicIDGenerator: Content-based ID generation
- PurityGuard: Context manager blocking nondeterministic operations
"""

import base64
import dataclasses
import hashlib
import json
import threading
from contextlib import contextmanager
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Type, Union


class LogicalClock:
    """
    Monotonic logical clock with no wall-clock dependency.
    
    Provides a thread-safe, persistable tick counter for ordering events
    without relying on system time. Implements Lamport-style logical time.
    
    Example:
        clock = LogicalClock()
        tick1 = clock.tick()  # Returns 1
        tick2 = clock.tick()  # Returns 2
        clock.save_state("clock.json")
        
        # Later...
        clock2 = LogicalClock()
        clock2.load_state("clock.json")
        tick3 = clock2.tick()  # Returns 3
    """
    
    def __init__(self, initial_tick: int = 0):
        """
        Initialize the logical clock.
        
        Args:
            initial_tick: Starting tick value (default 0)
        """
        if initial_tick < 0:
            raise ValueError("Initial tick must be non-negative")
        self._tick = initial_tick
        self._lock = threading.Lock()
    
    def tick(self) -> int:
        """
        Increment and return the current tick.
        
        Thread-safe atomic increment operation.
        
        Returns:
            The new tick value after increment
        """
        with self._lock:
            self._tick += 1
            return self._tick
    
    def get_tick(self) -> int:
        """
        Get the current tick without incrementing.
        
        Returns:
            The current tick value
        """
        with self._lock:
            return self._tick
    
    def merge(self, other_tick: int) -> int:
        """
        Merge with another clock's tick (Lamport merge).
        
        Sets tick to max(current, other) + 1.
        
        Args:
            other_tick: Tick value from another clock
            
        Returns:
            The new tick value after merge
        """
        with self._lock:
            self._tick = max(self._tick, other_tick) + 1
            return self._tick
    
    def save_state(self, path: Union[str, Path]) -> None:
        """
        Persist clock state to a file.
        
        Args:
            path: File path to save state
        """
        path = Path(path)
        with self._lock:
            state = {
                "tick": self._tick,
                "version": 1
            }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, path: Union[str, Path]) -> None:
        """
        Load clock state from a file.
        
        Args:
            path: File path to load state from
            
        Raises:
            FileNotFoundError: If the state file doesn't exist
            ValueError: If the state file is invalid
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        if "tick" not in state:
            raise ValueError("Invalid clock state: missing 'tick' field")
        
        tick = state["tick"]
        if not isinstance(tick, int) or tick < 0:
            raise ValueError(f"Invalid tick value: {tick}")
        
        with self._lock:
            self._tick = tick
    
    def __repr__(self) -> str:
        return f"LogicalClock(tick={self.get_tick()})"


class Canonicalizer:
    """
    Convert objects to canonical JSON-serializable form for stable hashing.
    
    Handles complex types including dicts, sets, dataclasses, enums,
    bytes, datetime objects, Decimals, Paths, and custom classes.
    
    Example:
        canon = Canonicalizer()
        digest = canon.stable_digest({"b": 2, "a": 1})  # Always same hash
        digest2 = canon.stable_digest({"a": 1, "b": 2})  # Same as above
    """
    
    # Types that are directly JSON-serializable
    PRIMITIVE_TYPES: Tuple[Type, ...] = (str, int, float, bool, type(None))
    
    def __init__(self, custom_handlers: Optional[Dict[Type, Any]] = None):
        """
        Initialize the canonicalizer.
        
        Args:
            custom_handlers: Optional dict mapping types to handler functions.
                            Handler signature: (obj) -> JSON-serializable value
        """
        self._custom_handlers = custom_handlers or {}
    
    def canonicalize(self, obj: Any) -> Any:
        """
        Convert any object to a canonical JSON-serializable form.
        
        Guarantees:
        - Dicts are sorted by key
        - Sets become sorted lists
        - Objects with same content produce identical output
        
        Args:
            obj: Any Python object
            
        Returns:
            JSON-serializable canonical representation
            
        Raises:
            TypeError: If object type cannot be canonicalized
        """
        # Check custom handlers first
        obj_type = type(obj)
        if obj_type in self._custom_handlers:
            return self._custom_handlers[obj_type](obj)
        
        # Primitives
        if isinstance(obj, self.PRIMITIVE_TYPES):
            return obj
        
        # Dict - sort by keys
        if isinstance(obj, dict):
            return {
                self._canonicalize_key(k): self.canonicalize(v)
                for k, v in sorted(obj.items(), key=lambda x: self._sort_key(x[0]))
            }
        
        # List/tuple - preserve order
        if isinstance(obj, (list, tuple)):
            return [self.canonicalize(item) for item in obj]
        
        # Set/frozenset - convert to sorted list
        if isinstance(obj, (set, frozenset)):
            return sorted(
                [self.canonicalize(item) for item in obj],
                key=self._sort_key
            )
        
        # Enum - use value
        if isinstance(obj, Enum):
            return {"__enum__": f"{obj.__class__.__name__}.{obj.name}", "value": obj.value}
        
        # Dataclass
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {
                "__dataclass__": obj.__class__.__name__,
                "fields": self.canonicalize(dataclasses.asdict(obj))
            }
        
        # Bytes - base64 encode
        if isinstance(obj, bytes):
            return {"__bytes__": base64.b64encode(obj).decode("ascii")}
        
        # Datetime types
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        if isinstance(obj, date):
            return {"__date__": obj.isoformat()}
        if isinstance(obj, time):
            return {"__time__": obj.isoformat()}
        if isinstance(obj, timedelta):
            return {"__timedelta__": obj.total_seconds()}
        
        # Decimal - string to preserve precision
        if isinstance(obj, Decimal):
            return {"__decimal__": str(obj)}
        
        # Path - string representation
        if isinstance(obj, Path):
            return {"__path__": str(obj)}
        
        # Custom classes with __dict__
        if hasattr(obj, "__dict__"):
            return {
                "__class__": obj.__class__.__qualname__,
                "__module__": obj.__class__.__module__,
                "attributes": self.canonicalize(vars(obj))
            }
        
        # Fallback - attempt str representation
        try:
            return {"__repr__": repr(obj), "__type__": type(obj).__name__}
        except Exception:
            raise TypeError(f"Cannot canonicalize object of type {type(obj).__name__}")
    
    def _canonicalize_key(self, key: Any) -> str:
        """Convert dict key to canonical string form."""
        if isinstance(key, str):
            return key
        if isinstance(key, (int, float, bool)):
            return str(key)
        if isinstance(key, Enum):
            return f"{key.__class__.__name__}.{key.name}"
        return repr(key)
    
    def _sort_key(self, obj: Any) -> Tuple[str, str]:
        """Generate a sort key for any object."""
        type_name = type(obj).__name__
        if isinstance(obj, self.PRIMITIVE_TYPES):
            return (type_name, str(obj) if obj is not None else "")
        if isinstance(obj, (dict, list, tuple, set, frozenset)):
            return (type_name, json.dumps(self.canonicalize(obj), sort_keys=True))
        return (type_name, repr(obj))
    
    def stable_digest(self, obj: Any) -> str:
        """
        Compute a stable SHA-256 hex digest of an object.
        
        Objects with identical content always produce the same digest,
        regardless of dict ordering or set iteration order.
        
        Args:
            obj: Any Python object
            
        Returns:
            64-character hex string (SHA-256)
        """
        return self.stable_digest_bytes(obj).hex()
    
    def stable_digest_bytes(self, obj: Any) -> bytes:
        """
        Compute a stable SHA-256 digest of an object as bytes.
        
        Args:
            obj: Any Python object
            
        Returns:
            32-byte SHA-256 digest
        """
        canonical = self.canonicalize(obj)
        json_bytes = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(json_bytes).digest()


class DeterministicIDGenerator:
    """
    Generate deterministic IDs from content hashes.
    
    No UUID, no randomness - purely deterministic from content.
    Given the same inputs, always produces the same ID.
    
    Example:
        gen = DeterministicIDGenerator()
        id1 = gen.generate_id("EC", "goal", "constraints")
        id2 = gen.generate_id("EC", "goal", "constraints")
        assert id1 == id2  # Always true
        # Result: "EC-a1b2c3d4e5f6..."
    """
    
    def __init__(
        self,
        hash_length: int = 16,
        canonicalizer: Optional[Canonicalizer] = None
    ):
        """
        Initialize the ID generator.
        
        Args:
            hash_length: Number of hex characters in the hash portion (default 16)
            canonicalizer: Optional Canonicalizer instance for content hashing
        """
        if hash_length < 4 or hash_length > 64:
            raise ValueError("hash_length must be between 4 and 64")
        self._hash_length = hash_length
        self._canonicalizer = canonicalizer or Canonicalizer()
    
    def generate_id(self, prefix: str, *content_parts: Any) -> str:
        """
        Generate a deterministic ID from a prefix and content parts.
        
        Args:
            prefix: ID prefix (e.g., "EC", "MEM", "OP")
            *content_parts: Any number of content objects to hash
            
        Returns:
            ID in format "PREFIX-hexhash" (e.g., "EC-a1b2c3d4e5f6...")
            
        Example:
            generate_id("EC", goal, constraints) -> "EC-a1b2c3d4e5f6..."
        """
        if not prefix:
            raise ValueError("Prefix cannot be empty")
        
        # Canonicalize all content parts
        content = [self._canonicalizer.canonicalize(part) for part in content_parts]
        
        # Include prefix in hash to avoid collisions across prefixes
        hash_input = {"prefix": prefix, "content": content}
        digest = self._canonicalizer.stable_digest(hash_input)
        
        return f"{prefix}-{digest[:self._hash_length]}"
    
    def generate_id_with_sequence(
        self,
        prefix: str,
        sequence: int,
        *content_parts: Any
    ) -> str:
        """
        Generate a deterministic ID with a sequence number.
        
        Useful when the same content might need multiple distinct IDs.
        
        Args:
            prefix: ID prefix
            sequence: Sequence number to include in hash
            *content_parts: Content objects to hash
            
        Returns:
            ID in format "PREFIX-hexhash"
        """
        return self.generate_id(prefix, sequence, *content_parts)
    
    def verify_id(self, id_str: str, prefix: str, *content_parts: Any) -> bool:
        """
        Verify that an ID matches the expected content.
        
        Args:
            id_str: ID to verify
            prefix: Expected prefix
            *content_parts: Expected content parts
            
        Returns:
            True if ID matches, False otherwise
        """
        expected = self.generate_id(prefix, *content_parts)
        return id_str == expected


class PurityGuard:
    """
    Context manager that blocks nondeterministic operations.
    
    Monkeypatches common sources of nondeterminism (datetime.now,
    uuid.uuid4, random.*) to raise errors when called inside the guard.
    
    Example:
        with PurityGuard():
            # This code must be pure - no randomness or time calls
            result = compute_something()
            
            # These would raise PurityViolationError:
            # datetime.now()  # Error!
            # uuid.uuid4()    # Error!
            # random.random() # Error!
    
    Warning:
        Not thread-safe for the patching itself. Use separate guards
        per thread or ensure single-threaded entry.
    """
    
    class PurityViolationError(RuntimeError):
        """Raised when a nondeterministic operation is attempted inside a PurityGuard."""
        pass
    
    _active_guards: int = 0
    _guard_lock = threading.Lock()
    _original_funcs: Dict[str, Any] = {}
    
    def __init__(self, allowed_operations: Optional[Set[str]] = None):
        """
        Initialize the purity guard.
        
        Args:
            allowed_operations: Optional set of operation names to allow
                              (e.g., {"datetime.now"} to allow time access)
        """
        self._allowed = allowed_operations or set()
    
    def __enter__(self) -> "PurityGuard":
        """Enter the purity guard context."""
        with self._guard_lock:
            if PurityGuard._active_guards == 0:
                self._install_patches()
            PurityGuard._active_guards += 1
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the purity guard context."""
        with self._guard_lock:
            PurityGuard._active_guards -= 1
            if PurityGuard._active_guards == 0:
                self._remove_patches()
    
    def _install_patches(self) -> None:
        """Install monkeypatches for nondeterministic functions."""
        import datetime as dt_module
        import random as random_module
        
        # Save originals
        PurityGuard._original_funcs = {
            "datetime.datetime.now": dt_module.datetime.now,
            "datetime.datetime.utcnow": dt_module.datetime.utcnow,
            "random.random": random_module.random,
            "random.randint": random_module.randint,
            "random.choice": random_module.choice,
            "random.shuffle": random_module.shuffle,
            "random.sample": random_module.sample,
            "random.uniform": random_module.uniform,
            "random.gauss": random_module.gauss,
            "random.randrange": random_module.randrange,
        }
        
        # Try to patch uuid if available
        try:
            import uuid as uuid_module
            PurityGuard._original_funcs["uuid.uuid4"] = uuid_module.uuid4
            PurityGuard._original_funcs["uuid.uuid1"] = uuid_module.uuid1
            uuid_module.uuid4 = self._make_blocker("uuid.uuid4")
            uuid_module.uuid1 = self._make_blocker("uuid.uuid1")
        except ImportError:
            pass
        
        # Install patches
        dt_module.datetime.now = self._make_blocker("datetime.now")
        dt_module.datetime.utcnow = self._make_blocker("datetime.utcnow")
        random_module.random = self._make_blocker("random.random")
        random_module.randint = self._make_blocker("random.randint")
        random_module.choice = self._make_blocker("random.choice")
        random_module.shuffle = self._make_blocker("random.shuffle")
        random_module.sample = self._make_blocker("random.sample")
        random_module.uniform = self._make_blocker("random.uniform")
        random_module.gauss = self._make_blocker("random.gauss")
        random_module.randrange = self._make_blocker("random.randrange")
    
    def _remove_patches(self) -> None:
        """Remove monkeypatches and restore original functions."""
        import datetime as dt_module
        import random as random_module
        
        originals = PurityGuard._original_funcs
        
        if "datetime.datetime.now" in originals:
            dt_module.datetime.now = originals["datetime.datetime.now"]
        if "datetime.datetime.utcnow" in originals:
            dt_module.datetime.utcnow = originals["datetime.datetime.utcnow"]
        if "random.random" in originals:
            random_module.random = originals["random.random"]
        if "random.randint" in originals:
            random_module.randint = originals["random.randint"]
        if "random.choice" in originals:
            random_module.choice = originals["random.choice"]
        if "random.shuffle" in originals:
            random_module.shuffle = originals["random.shuffle"]
        if "random.sample" in originals:
            random_module.sample = originals["random.sample"]
        if "random.uniform" in originals:
            random_module.uniform = originals["random.uniform"]
        if "random.gauss" in originals:
            random_module.gauss = originals["random.gauss"]
        if "random.randrange" in originals:
            random_module.randrange = originals["random.randrange"]
        
        try:
            import uuid as uuid_module
            if "uuid.uuid4" in originals:
                uuid_module.uuid4 = originals["uuid.uuid4"]
            if "uuid.uuid1" in originals:
                uuid_module.uuid1 = originals["uuid.uuid1"]
        except ImportError:
            pass
        
        PurityGuard._original_funcs = {}
    
    def _make_blocker(self, name: str) -> Any:
        """Create a blocker function for a given operation name."""
        allowed = self._allowed
        
        def blocker(*args: Any, **kwargs: Any) -> None:
            if name in allowed:
                # Call original if allowed
                original = PurityGuard._original_funcs.get(f"datetime.datetime.{name.split('.')[-1]}")
                if original is None:
                    original = PurityGuard._original_funcs.get(name)
                if original:
                    return original(*args, **kwargs)
            raise PurityGuard.PurityViolationError(
                f"Nondeterministic operation '{name}' is not allowed inside PurityGuard. "
                f"Use deterministic alternatives or add '{name}' to allowed_operations."
            )
        
        return blocker


@contextmanager
def pure_context(allowed_operations: Optional[Set[str]] = None) -> Iterator[PurityGuard]:
    """
    Convenience context manager for PurityGuard.
    
    Example:
        with pure_context():
            # Pure code only
            pass
    
    Args:
        allowed_operations: Optional set of operation names to allow
        
    Yields:
        The active PurityGuard instance
    """
    guard = PurityGuard(allowed_operations)
    with guard:
        yield guard


# Module-level convenience instances
_default_canonicalizer = Canonicalizer()
_default_id_generator = DeterministicIDGenerator()


def stable_hash(obj: Any) -> str:
    """
    Convenience function for stable hashing.
    
    Args:
        obj: Any Python object
        
    Returns:
        64-character hex string (SHA-256)
    """
    return _default_canonicalizer.stable_digest(obj)


def generate_deterministic_id(prefix: str, *content_parts: Any) -> str:
    """
    Convenience function for deterministic ID generation.
    
    Args:
        prefix: ID prefix
        *content_parts: Content to hash
        
    Returns:
        Deterministic ID string
    """
    return _default_id_generator.generate_id(prefix, *content_parts)


# Global logical clock instance
_default_logical_clock: Optional[LogicalClock] = None


def get_logical_clock() -> LogicalClock:
    """
    Get or create the global logical clock instance.
    
    Returns:
        The global LogicalClock instance
    """
    global _default_logical_clock
    if _default_logical_clock is None:
        _default_logical_clock = LogicalClock()
    return _default_logical_clock
