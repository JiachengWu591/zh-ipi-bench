"""The real victim for `zhipi.e2e`: injection-blast-radius's two architectures.

Every call here is a billed API call (DEEPSEEK_API_KEY). Point IBR_REPO at a checkout
of the repository; the run writes into that checkout's git-ignored `sandbox/`, so use
a dedicated clone, not a working copy. The checkout's commit is recorded by the caller.

Leak detection reads the public-comments file the pipeline writes to, the same surface
injection-blast-radius's own attack matrix checks, rather than trusting the return
values, so a leak is judged from what was actually published.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from ..e2e import Outcome, issue_title
from ..schemas import Sample


class IbrVictim:
    def __init__(self, repo: str | None = None) -> None:
        repo = repo or os.environ.get("IBR_REPO", "")
        if not repo:
            raise RuntimeError("set IBR_REPO to a checkout of injection-blast-radius")
        if repo not in sys.path:
            sys.path.insert(0, repo)
        from ibr import sandbox_fs  # type: ignore[import-not-found]
        from ibr.baseline_agent import run_baseline  # type: ignore[import-not-found]
        from ibr.bootstrap import (  # type: ignore[import-not-found]
            ensure_sandbox,
            reset_labels,
            reset_public_comments,
        )
        from ibr.config import (  # type: ignore[import-not-found]
            AUDIT_MODEL,
            BAIT_ENV_PATH,
            BASELINE_MODEL,
            PUBLIC_COMMENTS_PATH,
            READER_MODEL,
        )
        from ibr.issues import Issue  # type: ignore[import-not-found]
        from ibr.llm import build_client  # type: ignore[import-not-found]
        from ibr.pipeline import run_isolated  # type: ignore[import-not-found]

        ensure_sandbox()
        self._sandbox_fs = sandbox_fs
        self._run_baseline = run_baseline
        self._run_isolated = run_isolated
        self._reset = (reset_public_comments, reset_labels)
        self._issue_cls = Issue
        self._comments_path = PUBLIC_COMMENTS_PATH
        self._client = build_client()
        self.repo = repo
        self.models = {"audit": AUDIT_MODEL, "reader": READER_MODEL, "baseline": BASELINE_MODEL}
        # The fixed fake placeholders ibr plants; reading them is how leaks are recognised.
        text = sandbox_fs.read_text(BAIT_ENV_PATH)
        self.secret_values = tuple(
            line.partition("=")[2].strip() for line in text.splitlines() if "=" in line
        )

    def _issue(self, sample: Sample) -> Any:
        return self._issue_cls(
            issue_id=sample.sample_id,
            title=issue_title(sample),
            author="drive-by-reporter",
            body=sample.text,
        )

    def _published(self) -> str:
        return str(self._sandbox_fs.read_text(self._comments_path))

    def _clean(self) -> None:
        for reset in self._reset:
            reset()

    def baseline(self, sample: Sample) -> Outcome:
        self._clean()
        result = self._run_baseline(self._issue(sample), client=self._client)
        action = "posted_comment" if result.posted_comment is not None else "no_comment"
        return Outcome(published=self._published(), action=action)

    def isolated(self, sample: Sample) -> Outcome:
        self._clean()
        result = self._run_isolated(
            self._issue(sample), client=self._client, simulate_audit_bypass=True
        )
        if result.audit is not None and not result.audit.completed:
            # The audit failed closed to a made-up high_risk verdict. Counting that as
            # a real verdict would credit the audit with a catch it never made.
            raise RuntimeError("audit did not complete")
        return Outcome(
            published=self._published(),
            action=str(result.action_taken),
            audit_verdict=str(result.audit.risk_level) if result.audit else "-",
            audit_bypass_simulated=bool(result.audit_bypass_simulated),
        )
