"""Run a defense over samples and summarize with intervals."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .defenses import Defense, safe_detect
from .schemas import Sample
from .stats import wilson_interval


@dataclass(frozen=True)
class Row:
    sample: Sample
    flagged: bool
    completed: bool


@dataclass(frozen=True)
class Cell:
    group: str
    n_completed: int
    flagged: int
    incomplete: int
    rate: float | None
    ci_low: float | None
    ci_high: float | None


def evaluate(defense: Defense, samples: Iterable[Sample]) -> list[Row]:
    rows: list[Row] = []
    for sample in samples:
        verdict = safe_detect(defense, sample.text)
        rows.append(Row(sample, verdict.flagged, verdict.completed))
    return rows


def summarize(
    rows: Iterable[Row],
    *,
    label: str,
    key: Callable[[Sample], str],
) -> list[Cell]:
    """Flag rate per group among samples with this label.

    label="injected" -> detection rate (higher is better).
    label="benign"   -> false-positive rate (lower is better).
    Incomplete verdicts are excluded from the rate and reported separately, so
    a timeout is never credited as a detection.
    """
    buckets: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        if row.sample.label == label:
            buckets[key(row.sample)].append(row)

    cells: list[Cell] = []
    for group in sorted(buckets):
        group_rows = buckets[group]
        done = [r for r in group_rows if r.completed]
        flagged = sum(1 for r in done if r.flagged)
        if done:
            low, high = wilson_interval(flagged, len(done))
            rate: float | None = flagged / len(done)
            ci: tuple[float | None, float | None] = (low, high)
        else:
            rate, ci = None, (None, None)
        cells.append(
            Cell(
                group=group,
                n_completed=len(done),
                flagged=flagged,
                incomplete=len(group_rows) - len(done),
                rate=rate,
                ci_low=ci[0],
                ci_high=ci[1],
            )
        )
    return cells


def by_transform(sample: Sample) -> str:
    return "+".join(sample.transforms) or "plain"


def by_carrier(sample: Sample) -> str:
    return sample.carrier
