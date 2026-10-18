"""Interval estimates. Every rate this project reports carries one."""

from __future__ import annotations

from math import sqrt


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (default 95%).

    Preferred over the normal approximation because the rates here are often
    near 0 or 1 and the samples are small, where the normal interval escapes
    [0, 1] or collapses to zero width.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= successes <= n:
        raise ValueError("successes must be within [0, n]")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)
