"""
Timing utilities for real-time control, synchronizers, and benchmarking.
"""

import time
import numpy as np
from typing import List, Optional


class RateLimiter:
    """
    Maintains a steady target loop frequency (Hz) using monotonic sleep.
    """

    def __init__(self, frequency_hz: float):
        self.frequency = frequency_hz
        self.period = 1.0 / max(1e-5, frequency_hz)
        self.last_time = time.monotonic()

    def sleep(self):
        """Sleeps the remaining duration to adhere to target period."""
        now = time.monotonic()
        elapsed = now - self.last_time
        remaining = self.period - elapsed
        if remaining > 0.0:
            time.sleep(remaining)
        self.last_time = time.monotonic()

    def reset(self):
        self.last_time = time.monotonic()


class Timer:
    """
    Context manager and precision stopwatch for measuring block execution time.
    """

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self.start_time

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed * 1000.0


class LatencyStats:
    """
    Tracks streaming and synchronization latency samples and computes p50, p95, p99.
    """

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.samples: List[float] = []

    def record(self, latency_sec: float):
        self.samples.append(latency_sec)
        if len(self.samples) > self.max_samples:
            self.samples.pop(0)

    def summary(self) -> dict:
        if not self.samples:
            return {"count": 0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
        arr = np.array(self.samples) * 1000.0
        return {
            "count": len(arr),
            "mean_ms": float(np.mean(arr)),
            "p50_ms": float(np.percentile(arr, 50)),
            "p95_ms": float(np.percentile(arr, 95)),
            "p99_ms": float(np.percentile(arr, 99)),
            "max_ms": float(np.max(arr)),
        }
