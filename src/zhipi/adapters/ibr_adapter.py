"""Use the injection-blast-radius security audit as a `Defense`.

Scope of this adapter, stated so it is not over-read: it wraps only
`ibr.pipeline.audit_only` (the probabilistic screening layer). It does NOT run
the isolated pipeline end to end, so it says nothing about the structural
layer. Wiring `run_isolated` in (so the benchmark can ask "does the structural
layer hold on Chinese input?") is a Phase 4 task in docs/ROADMAP.md.

`ibr` is not a pip package; point IBR_REPO at a checkout of the repo. Calling
`detect` makes a real, billed API call (DEEPSEEK_API_KEY).
"""

from __future__ import annotations

import os
import sys
from typing import Any

from ..defenses import Verdict
from ..schemas import Sample


def _import_ibr() -> tuple[Any, Any]:
    repo = os.environ.get("IBR_REPO", "")
    if not repo:
        raise RuntimeError("set IBR_REPO to a checkout of injection-blast-radius")
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from ibr.issues import Issue  # type: ignore[import-not-found]
    from ibr.pipeline import audit_only  # type: ignore[import-not-found]

    return Issue, audit_only


class IbrAuditDefense:
    """flagged == the audit returned a risk level in `flag_on`.

    The audit's `suspicious` verdict does not short-circuit in ibr (it passes
    through to the Reader with a review flag), so by default only `high_risk`
    counts as flagged. Pass `flag_on=("suspicious", "high_risk")` to measure the
    stricter reading; report both.
    """

    name = "ibr-audit"

    def __init__(self, flag_on: tuple[str, ...] = ("high_risk",)) -> None:
        self._issue_cls, self._audit_only = _import_ibr()
        self._flag_on = flag_on

    def detect(self, text: str) -> Verdict:
        issue = self._issue_cls(
            issue_id="zhipi-probe",
            title="(untitled)",
            author="drive-by-reporter",
            body=text,
        )
        verdict = self._audit_only(issue)
        return Verdict(
            flagged=verdict.risk_level in self._flag_on,
            detail=str(verdict.risk_level),
            completed=bool(verdict.completed),
        )


def issue_for(sample: Sample) -> Any:
    """Build an ibr `Issue` from a sample (sample ids already fit ibr's id rule)."""
    issue_cls, _ = _import_ibr()
    return issue_cls(
        issue_id=sample.sample_id,
        title="(untitled)",
        author="drive-by-reporter",
        body=sample.text,
    )
