"""Interval estimates. Every rate this project reports carries one."""

from __future__ import annotations

import random
from math import comb, sqrt


def auroc(positives: list[float], negatives: list[float]) -> float:
    """P(a random positive scores above a random negative); ties count half.

    Threshold-free, so it separates "this detector ranks injections above benign text
    worse here" from "it is merely calibrated differently here".
    """
    if not positives or not negatives:
        raise ValueError("need at least one positive and one negative")
    wins = sum((p > n) + 0.5 * (p == n) for p in positives for n in negatives)
    return wins / (len(positives) * len(negatives))


def auroc_bootstrap_ci(
    positives: list[float],
    negatives: list[float],
    *,
    resamples: int = 400,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap interval for the AUROC (fixed seed, so reports are stable).

    Resamples individual samples, so it ignores that samples from one intent are
    correlated; the interval is a lower bound on the real uncertainty.
    """
    rng = random.Random(seed)
    draws = sorted(
        auroc(
            [rng.choice(positives) for _ in positives],
            [rng.choice(negatives) for _ in negatives],
        )
        for _ in range(resamples)
    )
    return draws[int(alpha / 2 * resamples)], draws[int((1 - alpha / 2) * resamples) - 1]


def mcnemar_exact(lost: int, gained: int) -> float:
    """Two-sided exact McNemar p-value for paired binary outcomes.

    `lost`: pairs the baseline got right and the variant got wrong; `gained`: the
    reverse. Pairs where both agree carry no information and are not counted. Under
    "the variant changes nothing", each discordant pair is a fair coin flip, so the
    p-value is the binomial tail on n = lost + gained. No discordant pairs -> 1.0.
    """
    n = lost + gained
    if n == 0:
        return 1.0
    tail = sum(comb(n, k) for k in range(min(lost, gained) + 1)) / 2**n
    return min(1.0, 2 * tail)


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
