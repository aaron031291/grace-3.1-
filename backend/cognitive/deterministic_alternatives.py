"""
Deterministic Alternatives - Replace All Probabilistic Operations

This module provides deterministic alternatives to probabilistic operations:
- Deterministic sampling (no randomness)
- Deterministic selection (priority-based)
- Deterministic uncertainty (confidence intervals, not probabilities)
- Deterministic scheduling
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from collections import OrderedDict
import hashlib

logger = logging.getLogger(__name__)


class DeterministicSampler:
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
            # Deterministic selection: use hash-based ordering
            scored_items = [
                (item, self._deterministic_hash(item))
                for item in items
            ]
            scored_items.sort(key=lambda x: x[1])
            return [item for item, _ in scored_items[:n]]
    
    def _deterministic_hash(self, item: Any) -> int:
        """Generate deterministic hash for item."""
        content = str(item) + (str(self.seed) if self.seed else "")
        return int(hashlib.md5(content.encode()).hexdigest(), 16)
    
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
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize deterministic random replacement.
        
        Args:
            seed: Seed for reproducibility (not for randomness)
        """
        self.seed = seed
        self.counter = 0
    
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
        
        Uses round-robin with counter.
        """
        if n >= len(items):
            return items.copy()
        
        selected = []
        for i in range(n):
            index = (self.counter + i) % len(items)
            if items[index] not in selected:
                selected.append(items[index])
        
        self.counter += n
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
