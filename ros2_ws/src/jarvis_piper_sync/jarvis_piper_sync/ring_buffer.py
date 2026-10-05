"""
JARVIS PiPER High-Performance Temporal Ring Buffer
Enables microsecond-precision time alignment, jitter monitoring, and zero-copy lookups.
"""

import bisect
import threading
import time
from typing import Any, Dict, List, Optional, Tuple


class TemporalRingBuffer:
    """Thread-safe circular ring buffer indexing messages by floating-point timestamp (seconds)."""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._lock = threading.Lock()
        self._timestamps: List[float] = []
        self._items: List[Any] = []
        self._total_pushed = 0
        self._dropped_count = 0
        self._last_jitter_ms = 0.0
        self._intervals: List[float] = []

    def push(self, timestamp: float, item: Any) -> None:
        """Pushes a timestamped item into the buffer while keeping timestamps sorted."""
        with self._lock:
            self._total_pushed += 1
            if self._timestamps:
                dt = timestamp - self._timestamps[-1]
                if dt > 0:
                    self._intervals.append(dt)
                    if len(self._intervals) > 100:
                        self._intervals.pop(0)
                    mean_dt = sum(self._intervals) / len(self._intervals)
                    self._last_jitter_ms = abs(dt - mean_dt) * 1000.0

            # Insert in sorted position
            idx = bisect.bisect_right(self._timestamps, timestamp)
            self._timestamps.insert(idx, timestamp)
            self._items.insert(idx, item)

            # Evict oldest if exceeding capacity
            if len(self._timestamps) > self.capacity:
                self._timestamps.pop(0)
                self._items.pop(0)
                self._dropped_count += 1

    def get_nearest(self, target_time: float, max_slop_sec: float = 0.05) -> Tuple[Optional[Any], float]:
        """
        Finds the element nearest to `target_time` within `max_slop_sec`.
        Returns (item, actual_time_difference_in_seconds) or (None, inf).
        """
        with self._lock:
            if not self._timestamps:
                return None, float("inf")

            idx = bisect.bisect_left(self._timestamps, target_time)
            best_idx = None
            min_diff = float("inf")

            candidates = [idx - 1, idx, idx + 1]
            for c in candidates:
                if 0 <= c < len(self._timestamps):
                    diff = abs(self._timestamps[c] - target_time)
                    if diff < min_diff:
                        min_diff = diff
                        best_idx = c

            if best_idx is not None and min_diff <= max_slop_sec:
                return self._items[best_idx], min_diff
            return None, min_diff

    def get_latest(self) -> Tuple[Optional[Any], float]:
        """Returns the most recent item and its timestamp."""
        with self._lock:
            if not self._timestamps:
                return None, 0.0
            return self._items[-1], self._timestamps[-1]

    def get_metrics(self) -> Dict[str, Any]:
        """Returns diagnostic metrics."""
        with self._lock:
            size = len(self._timestamps)
            avg_rate = 0.0
            if len(self._intervals) > 1:
                avg_dt = sum(self._intervals) / len(self._intervals)
                if avg_dt > 0:
                    avg_rate = 1.0 / avg_dt
            return {
                "size": size,
                "capacity": self.capacity,
                "total_pushed": self._total_pushed,
                "dropped_oldest": self._dropped_count,
                "estimated_hz": round(avg_rate, 2),
                "jitter_ms": round(self._last_jitter_ms, 2),
            }

    def clear(self) -> None:
        """Clears the ring buffer."""
        with self._lock:
            self._timestamps.clear()
            self._items.clear()
            self._intervals.clear()
