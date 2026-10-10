"""Small, dependency-free quality helpers used by the v3.5 test harness."""
from __future__ import annotations
import math
import time


def timed(fn, iterations: int = 1):
    """Return elapsed seconds and last result for deterministic micro-benchmarks."""
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    start = time.perf_counter()
    result = None
    for _ in range(iterations):
        result = fn()
    return time.perf_counter() - start, result


def finite_number(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def clamp_percent(value) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, value))
