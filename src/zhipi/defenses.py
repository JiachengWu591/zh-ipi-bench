"""The interface every defense under test implements, plus sanity baselines.

The keyword baselines below exist to test the harness, not to be a result: they
are deliberately naive. A number measured on them says nothing about real
detectors. Real ones (Prompt Guard 2, Qwen3Guard, an LLM judge, the
injection-blast-radius audit) plug in through the same `Defense` protocol.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Verdict:
    flagged: bool
    score: float | None = None
    completed: bool = True
    """False when the defense errored or timed out.

    A failed check fails closed (flagged=True), but it must not be counted as a
    *detection*: a caller measuring detection rate counts only completed
    verdicts, and reports the incomplete ones separately.
    """


class Defense(Protocol):
    name: str

    def detect(self, text: str) -> Verdict: ...


def safe_detect(defense: Defense, text: str) -> Verdict:
    """Run a defense; any exception becomes a fail-closed, incomplete verdict."""
    try:
        return defense.detect(text)
    except Exception:  # noqa: BLE001 - a broken check must never read as clean
        return Verdict(flagged=True, completed=False)


@dataclass(frozen=True)
class RegexDefense:
    name: str
    patterns: tuple[re.Pattern[str], ...]

    def detect(self, text: str) -> Verdict:
        hits = sum(1 for pattern in self.patterns if pattern.search(text))
        return Verdict(flagged=hits > 0, score=float(hits))


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


EN_KEYWORDS = RegexDefense(
    name="keyword-en",
    patterns=_compile(
        r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+"
        r"(instructions|prompts|rules)",
        r"disregard\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above)",
        r"you\s+are\s+now\b",
        r"system\s+prompt",
    ),
)

ZH_KEYWORDS = RegexDefense(
    name="keyword-zh",
    patterns=_compile(
        r"忽略.{0,6}(指令|提示|规则|要求)",
        r"无视.{0,6}(指令|提示|规则|要求)",
        r"你现在是",
        r"系统提示",
    ),
)
