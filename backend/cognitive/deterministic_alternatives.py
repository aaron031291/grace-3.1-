import logging
import json
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
import hashlib

from cognitive.deterministic_primitives import (
    Canonicalizer, stable_hash
)


class DeterministicSampler:
    logger = logging.getLogger(__name__)
    """
    Deterministic sampling - no randomness, all selections are provable.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize deterministic sampler.
        
        Args:
            seed: Optional seed (for reproducibility, not randomness)
        """
        self.seed = seed
        self.sample_history: List[Dict[str, Any]] = []
        self.canonicalizer = Canonicalizer()
    
    def deterministic_sample(
        self,
        items: List[Any],
        n: int,
        priority_function: Optional[Callable[[Any], float]] = None
    ) -> List[Any]:
        """
        Deterministically sample n items.
        
        Uses priority-based selection, not randomness.
        
        Args:
            items: Items to sample from
            n: Number of items to select
            priority_function: Function to calculate priority (higher = selected first)
            
        Returns:
            List of selected items (deterministic order)
        """
        if n >= len(items):
            return items.copy()
        
        if priority_function:
            # Sort by priority (deterministic)
            scored_items = [
                (item, priority_function(item))
                for item in items
            ]
            scored_items.sort(key=lambda x: x[1], reverse=True)
            return [item for item, _ in scored_items[:n]]
        else:
            # Deterministic selection: use stable_digest for proper canonicalization
            # This fixes the issue where str(item) is unstable for dicts/sets
            scored_items = [
                (item, self._deterministic_hash(item))
                for item in items
            ]
            scored_items.sort(key=lambda x: x[1])
            return [item for item, _ in scored_items[:n]]
    
    def _deterministic_hash(self, item: Any) -> str:
        """Generate deterministic hash for item using proper canonicalization."""
        if self.seed is not None:
            # Include seed in the hash input
            content = {"item": item, "seed": self.seed}
        else:
            content = {"item": item}
        return self.canonicalizer.stable_digest(content)
    
    def weighted_sample(
        self,
        items: List[Any],
        weights: List[float],
        n: int
    ) -> List[Any]:
        """
        Deterministic weighted sampling.
        
        Uses cumulative distribution, not random sampling.
        """
        if len(items) != len(weights):
            raise ValueError("Items and weights must have same length")
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return items[:n]
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Create cumulative distribution
        cumulative = []
        cumsum = 0.0
        for w in normalized_weights:
            cumsum += w
            cumulative.append(cumsum)
        
        # Deterministic selection: select items at evenly spaced points
        selected = []
        for i in range(n):
            target = (i + 1) / (n + 1)  # Evenly spaced
            # Find item at this point in cumulative distribution
            for j, cum in enumerate(cumulative):
                if cum >= target:
                    if items[j] not in selected:
                        selected.append(items[j])
                    break
        
        return selected


class DeterministicSelector:
    """
    Deterministic selection - replaces random.choice, random.sample, etc.
    """
    
    @staticmethod
    def select_by_priority(
        items: List[Any],
        priority_function: Callable[[Any], float],
        n: int = 1
    ) -> List[Any]:
        """
        Select items by priority (deterministic).
        
        Args:
            items: Items to select from
            priority_function: Function returning priority (higher = better)
            n: Number of items to select
            
        Returns:
            List of selected items (sorted by priority)
        """
        scored = [(item, priority_function(item)) for item in items]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored[:n]]
    
    @staticmethod
    def select_by_criteria(
        items: List[Any],
        criteria: List[Callable[[Any], bool]],
        n: int = 1
    ) -> List[Any]:
        """
        Select items that meet all criteria (deterministic).
        
        Args:
            items: Items to select from
            criteria: List of criteria functions (must all return True)
            n: Number of items to select
            
        Returns:
            List of items meeting all criteria
        """
        filtered = items
        for criterion in criteria:
            filtered = [item for item in filtered if criterion(item)]
        
        return filtered[:n]
    
    @staticmethod
    def select_round_robin(
        items: List[Any],
        n: int,
        start_index: int = 0
    ) -> List[Any]:
        """
        Round-robin selection (deterministic).
        
        Args:
            items: Items to select from
            n: Number of items to select
            start_index: Starting index
            
        Returns:
            List of selected items
        """
        if not items:
            return []
        
        selected = []
        for i in range(n):
            index = (start_index + i) % len(items)
            selected.append(items[index])
        
        return selected


class DeterministicUncertainty:
    """
    Deterministic uncertainty quantification - no probabilities, only confidence intervals.
    """
    
    @staticmethod
    def calculate_confidence_interval(
        values: List[float],
        confidence_level: float = 0.95
    ) -> Tuple[float, float, float]:
        """
        Calculate confidence interval deterministically.
        
        Args:
            values: List of values
            confidence_level: Confidence level (0.95 = 95%)
            
        Returns:
            Tuple of (mean, lower_bound, upper_bound)
        """
        if not values:
            return 0.0, 0.0, 0.0
        
        # Calculate mean (deterministic)
        mean = sum(values) / len(values)
        
        # Calculate standard deviation (deterministic)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # Calculate confidence interval (deterministic)
        # Using z-score for normal distribution approximation
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576
        }
        z_score = z_scores.get(confidence_level, 1.96)
        
        margin = z_score * std_dev / (len(values) ** 0.5)
        lower = mean - margin
        upper = mean + margin
        
        return mean, lower, upper
    
    @staticmethod
    def calculate_uncertainty_from_intervals(
        intervals: List[Tuple[float, float]]
    ) -> Tuple[float, float, float]:
        """
        Calculate uncertainty from multiple confidence intervals.
        
        Args:
            intervals: List of (lower, upper) confidence intervals
            
        Returns:
            Tuple of (mean_lower, mean_upper, uncertainty_width)
        """
        if not intervals:
            return 0.0, 0.0, 0.0
        
        # Calculate mean bounds (deterministic)
        mean_lower = sum(lower for lower, _ in intervals) / len(intervals)
        mean_upper = sum(upper for _, upper in intervals) / len(intervals)
        
        # Uncertainty width
        uncertainty = mean_upper - mean_lower
        
        return mean_lower, mean_upper, uncertainty


class DeterministicSorter:
    """
    Deterministic sorting - always produces same order for same input.
    """
    
    @staticmethod
    def stable_sort(
        items: List[Any],
        key_function: Callable[[Any], Any],
        reverse: bool = False
    ) -> List[Any]:
        """
        Stable deterministic sort.
        
        Args:
            items: Items to sort
            key_function: Function to extract sort key
            reverse: If True, sort in reverse order
            
        Returns:
            Sorted list (deterministic)
        """
        # Use tuple sorting for stability
        # Include original index to ensure stability
        indexed_items = [
            (key_function(item), i, item)
            for i, item in enumerate(items)
        ]
        
        indexed_items.sort(reverse=reverse)
        
        return [item for _, _, item in indexed_items]
    
    @staticmethod
    def multi_key_sort(
        items: List[Any],
        key_functions: List[Callable[[Any], Any]],
        reverse: List[bool] = None
    ) -> List[Any]:
        """
        Sort by multiple keys (deterministic).
        
        Args:
            items: Items to sort
            key_functions: List of key functions (priority order)
            reverse: List of reverse flags for each key
            
        Returns:
            Sorted list
        """
        if reverse is None:
            reverse = [False] * len(key_functions)
        
        # Create sort keys
        indexed_items = [
            (
                tuple(key_func(item) for key_func in key_functions),
                i,
                item
            )
            for i, item in enumerate(items)
        ]
        
        # Sort with reverse flags
        def sort_key(x):
            keys, idx, item = x
            result = []
            for i, (key, rev) in enumerate(zip(keys, reverse)):
                result.append(-key if rev else key)
            return tuple(result)
        
        indexed_items.sort(key=sort_key)
        
        return [item for _, _, item in indexed_items]


class DeterministicRandomReplacement:
    """
    Deterministic replacement for random operations.
    
    Provides deterministic alternatives to:
    - random.choice() → deterministic_choice()
    - random.sample() → deterministic_sample()
    - random.shuffle() → deterministic_shuffle()
    """
    
    def __init__(self, seed: Optional[int] = None, stream_id: Optional[str] = None):
        """
        Initialize deterministic random replacement.
        
        Args:
            seed: Seed for reproducibility (not for randomness)
            stream_id: Optional stream identifier for persistence
        """
        self.seed = seed
        self.counter = 0
        self.stream_id = stream_id
        self._persistence_path: Optional[Path] = None
    
    def persist_counter(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Persist counter state to file or return as dict.
        
        Args:
            path: Optional file path to save to. If None, returns dict.
            
        Returns:
            Dict with counter state keyed by stream_id
        """
        key = self.stream_id or "_default"
        state = {
            key: {
                "counter": self.counter,
                "seed": self.seed,
            }
        }
        
        if path is not None:
            path = Path(path)
            # Merge with existing state if file exists
            existing = {}
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, IOError):
                    existing = {}
            existing.update(state)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            return existing
        
        return state
    
    def load_counter(self, path: Optional[Path] = None, state: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load counter state from file or dict.
        
        Args:
            path: Optional file path to load from
            state: Optional dict to load from (used if path is None)
            
        Returns:
            True if state was loaded, False otherwise
        """
        key = self.stream_id or "_default"
        
        if path is not None:
            path = Path(path)
            if not path.exists():
                return False
            try:
                with open(path, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except (json.JSONDecodeError, IOError):
                return False
        
        if state is None:
            return False
        
        if key in state:
            stream_state = state[key]
            self.counter = stream_state.get("counter", 0)
            if "seed" in stream_state and self.seed is None:
                self.seed = stream_state["seed"]
            return True
        
        return False
    
    @contextmanager
    def with_stream(self, stream_id: str):
        """
        Context manager for using a specific stream_id temporarily.
        
        Args:
            stream_id: Stream identifier to use within context
            
        Yields:
            Self with stream_id set
        """
        old_stream_id = self.stream_id
        old_counter = self.counter
        self.stream_id = stream_id
        try:
            yield self
        finally:
            self.stream_id = old_stream_id
            self.counter = old_counter
    
    def deterministic_choice(self, items: List[Any]) -> Any:
        """
        Deterministically choose an item.
        
        Uses counter-based selection, not randomness.
        """
        if not items:
            raise ValueError("Cannot choose from empty list")
        
        index = self.counter % len(items)
        self.counter += 1
        return items[index]
    
    def deterministic_sample(
        self,
        items: List[Any],
        n: int
    ) -> List[Any]:
        """
        Deterministically sample n items.
        
        Uses round-robin with counter. Uses a set of digests for O(1) lookup
        instead of O(n) list membership check.
        """
        if n >= len(items):
            return items.copy()
        
        selected = []
        selected_digests: set = set()  # O(1) lookup using stable_hash
        attempts = 0
        max_attempts = len(items) * 2  # Prevent infinite loop
        
        while len(selected) < n and attempts < max_attempts:
            index = (self.counter + attempts) % len(items)
            item = items[index]
            item_digest = stable_hash(item)
            
            if item_digest not in selected_digests:
                selected.append(item)
                selected_digests.add(item_digest)
            
            attempts += 1
        
        self.counter += attempts
        return selected
    
    def deterministic_shuffle(self, items: List[Any]) -> List[Any]:
        """
        Deterministically shuffle items.
        
        Uses deterministic permutation based on counter.
        """
        if not items:
            return items.copy()
        
        # Create deterministic permutation
        permuted = items.copy()
        n = len(permuted)
        
        # Use counter to determine swap positions
        for i in range(n - 1, 0, -1):
            j = (self.counter + i) % (i + 1)
            permuted[i], permuted[j] = permuted[j], permuted[i]
        
        self.counter += 1
        return permuted


class DeterministicTraceStore:
    """
    Store operation traces efficiently using digests instead of full payloads.
    
    Provides compact storage for tracing deterministic operations without
    duplicating full payload data.
    """
    
    def __init__(self, max_entries: int = 10000):
        """
        Initialize the trace store.
        
        Args:
            max_entries: Maximum number of entries before auto-pruning
        """
        self.max_entries = max_entries
        self._traces: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._canonicalizer = Canonicalizer()
    
    def store_trace(self, trace_digest: str, summary: Dict[str, Any]) -> None:
        """
        Store a trace by its digest with a summary.
        
        Args:
            trace_digest: SHA-256 digest of the trace payload
            summary: Summary metadata (not the full payload)
        """
        # Auto-prune if at capacity
        if len(self._traces) >= self.max_entries:
            self.prune_old(self.max_entries // 2)
        
        # Move to end if exists (LRU behavior)
        if trace_digest in self._traces:
            self._traces.move_to_end(trace_digest)
        
        self._traces[trace_digest] = {
            "summary": summary,
            "stored_at_tick": len(self._traces),
        }
    
    def get_trace(self, digest: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a trace by its digest.
        
        Args:
            digest: SHA-256 digest of the trace
            
        Returns:
            Trace summary if found, None otherwise
        """
        trace = self._traces.get(digest)
        if trace:
            # Move to end on access (LRU behavior)
            self._traces.move_to_end(digest)
            return trace.copy()
        return None
    
    def prune_old(self, max_entries: int) -> int:
        """
        Prune oldest entries to stay under max_entries.
        
        Args:
            max_entries: Maximum entries to keep
            
        Returns:
            Number of entries pruned
        """
        if max_entries < 0:
            max_entries = 0
        
        pruned = 0
        while len(self._traces) > max_entries:
            self._traces.popitem(last=False)  # Remove oldest
            pruned += 1
        
        return pruned
    
    def has_trace(self, digest: str) -> bool:
        """Check if a trace exists."""
        return digest in self._traces
    
    def count(self) -> int:
        """Return number of stored traces."""
        return len(self._traces)
    
    def clear(self) -> None:
        """Clear all traces."""
        self._traces.clear()
    
    def compute_digest(self, payload: Any) -> str:
        """
        Compute digest for a payload (helper method).
        
        Args:
            payload: Any payload to hash
            
        Returns:
            SHA-256 hex digest
        """
        return self._canonicalizer.stable_digest(payload)
