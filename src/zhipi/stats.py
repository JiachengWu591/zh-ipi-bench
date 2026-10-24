"""Interval estimates. Every rate this project reports carries one."""

from __future__ import annotations

import random
from math import comb, sqrt


def fisher_exact(a: int, n1: int, b: int, n2: int) -> float:
    """Two-sided Fisher exact p-value for a: x/n1 vs b: y/n2 (successes a of n1, b of n2).

    Sums the probability of every table at least as unlikely as the observed one, under
    the null that both groups share one rate. Uses only integer binomials, so it is
    exact for the sizes used here. Treats runs as independent, which repeated runs of
    the same sample are not; read the result as a lower bound on the true p-value.
    """
    if min(a, b) < 0 or a > n1 or b > n2 or n1 <= 0 or n2 <= 0:
        raise ValueError("invalid counts")
    total, k = n1 + n2, a + b
    denom = comb(total, k)

    def prob(x: int) -> float:
        return comb(n1, x) * comb(n2, k - x) / denom

    observed = prob(a)
    lo, hi = max(0, k - n2), min(k, n1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= observed * (1 + 1e-9)))


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


def cohen_kappa(first: list[str], second: list[str]) -> float | None:
    """Cohen's kappa for two raters over the same items (any number of categories).

    None when it is undefined: no items, or both raters used one single category so chance
    agreement is already 1. Kappa depends on how common each category is, so it is only
    comparable between packets with similar label mixes; report raw agreement beside it.
    """
    if len(first) != len(second):
        raise ValueError("raters must label the same items")
    n = len(first)
    if n == 0:
        return None
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    expected = sum(
        (first.count(c) / n) * (second.count(c) / n) for c in set(first) | set(second)
    )
    if expected >= 1.0:
        return None
    return (observed - expected) / (1 - expected)


def kappa_bootstrap_ci(
    first: list[str],
    second: list[str],
    *,
    resamples: int = 1000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float] | None:
    """Percentile bootstrap interval for kappa (fixed seed). Resamples items, so it ignores
    that items drawn from one intent are correlated: a lower bound on the uncertainty.
    Resamples where kappa is undefined are dropped; None if too few remain."""
    rng = random.Random(seed)
    n = len(first)
    draws: list[float] = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        value = cohen_kappa([first[i] for i in idx], [second[i] for i in idx])
        if value is not None:
            draws.append(value)
    if len(draws) < resamples // 2:
        return None
    draws.sort()
    return draws[int(alpha / 2 * len(draws))], draws[int((1 - alpha / 2) * len(draws)) - 1]


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
