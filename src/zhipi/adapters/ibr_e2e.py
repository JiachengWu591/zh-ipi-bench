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
from .openai_compat import CompatClient, build_local_client


class IbrVictim:
    """Both architectures on one model.

    With no `base_url` it uses injection-blast-radius's own DeepSeek client and models.
    With `base_url` (an OpenAI-compatible server, e.g. a local llama.cpp) and `model`,
    *both* architectures and every stage (baseline agent, audit, reader) use that one
    model through `CompatClient`, so the comparison between architectures is not
    confounded by a different brain.
    """

    def __init__(
        self,
        repo: str | None = None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        tool_choice_mode: str = "named",
        request_log: list[dict[str, Any]] | None = None,
    ) -> None:
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
        self.repo = repo
        self._model_args: dict[str, dict[str, str]] = {"baseline": {}, "isolated": {}}
        if base_url:
            if not model:
                raise ValueError("a custom base_url needs --victim-model")
            self._client = CompatClient(
                build_local_client(base_url), tool_choice_mode=tool_choice_mode, log=request_log
            )
            self.models = {"audit": model, "reader": model, "baseline": model}
            self._model_args = {
                "baseline": {"model": model},
                "isolated": {"audit_model": model, "reader_model": model},
            }
        else:
            self._client = build_client()
            self.models = {
                "audit": AUDIT_MODEL, "reader": READER_MODEL, "baseline": BASELINE_MODEL,
            }
        self.base_url = base_url or ""
        self.tool_choice_mode = tool_choice_mode if base_url else "n/a"
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
        result = self._run_baseline(
            self._issue(sample), client=self._client, **self._model_args["baseline"]
        )
        action = "posted_comment" if result.posted_comment is not None else "no_comment"
        return Outcome(published=self._published(), action=action)

    def isolated(self, sample: Sample) -> Outcome:
        self._clean()
        result = self._run_isolated(
            self._issue(sample),
            client=self._client,
            simulate_audit_bypass=True,
            **self._model_args["isolated"],
        )
        verdict = "-"
        if result.audit is not None:
            # An audit that failed fails closed to a made-up high_risk. Record it as
            # `audit_failed` so it is never credited as a catch; the run itself still
            # counts, because the reader and executor ran regardless.
            verdict = str(result.audit.risk_level) if result.audit.completed else "audit_failed"
        return Outcome(
            published=self._published(),
            action=str(result.action_taken),
            audit_verdict=verdict,
            audit_bypass_simulated=bool(result.audit_bypass_simulated),
        )
